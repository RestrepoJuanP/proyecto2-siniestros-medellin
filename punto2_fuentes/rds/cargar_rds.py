"""
Carga la fuente relacional del proyecto en RDS MariaDB (base "movilidad").

Pasos:
1. Aplica esquema.sql (idempotente).
2. Catálogo de comunas: consulta agregada a la capa ArcGIS VM_Accidentes
   (num_comuna, nom_comuna, todos los años).
3. Catálogo de barrios: consulta agregada por barrio y num_comuna (todos los años).
4. Siniestros 2019-2022: descarga paginada (where anio <= 2022), copia en
   datos_locales/siniestros_2019_2022.csv, transformación de tipos y carga en
   lotes con INSERT ... ON DUPLICATE KEY UPDATE.
5. Reporte final: filas por tabla, filas por año, radicados duplicados y
   siniestros con codigo_comuna NULL.

Opciones:
  --solo-descarga   Descarga y transforma sin conectarse a la base (prueba local).
  --usar-csv-local  Usa datos_locales/siniestros_2019_2022.csv en vez de descargar
                    otra vez los siniestros (la descarga tarda ~20-30 min).

Variables de entorno (.env): RDS_HOST, RDS_PUERTO, RDS_USUARIO, RDS_CLAVE, RDS_BASE
y opcionalmente URL_ARCGIS_ACCIDENTES.

Uso (desde la raíz del repositorio): python punto2_fuentes/rds/cargar_rds.py
"""

import argparse
import json
import logging
import math
import os
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import pymysql
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
registro = logging.getLogger(__name__)

URL_ACCIDENTES_POR_DEFECTO = "https://www.medellin.gov.co/servidormapas/rest/services/transporte/VM_Accidentes/MapServer/0"

CARPETA_SCRIPT = Path(__file__).resolve().parent
CARPETA_RAIZ_PROYECTO = CARPETA_SCRIPT.parent.parent
ARCHIVO_ESQUEMA = CARPETA_SCRIPT / "esquema.sql"
ARCHIVO_CSV_SINIESTROS = CARPETA_RAIZ_PROYECTO / "datos_locales" / "siniestros_2019_2022.csv"

FILTRO_SINIESTROS_RDS = "anio <= 2022"
TAMANO_PAGINA_ARCGIS = 2000
TAMANO_LOTE_INSERCION = 1000
NUMERO_INTENTOS = 3
SEGUNDOS_ESPERA_ENTRE_INTENTOS = 5
SEGUNDOS_TIMEOUT = 180

# Conteos por año observados en la exploración del Módulo 1 (solo como referencia;
# la capa se sigue validando y puede cambiar, por eso también se compara contra la capa en vivo).
CONTEOS_REFERENCIA_MODULO1 = {2019: 46551, 2020: 31755, 2021: 40655, 2022: 38642}

COLUMNAS_SINIESTROS = [
    "objectid",
    "radicado",
    "fecha_siniestro",
    "hora_siniestro",
    "dia",
    "mes",
    "anio",
    "clase_siniestro",
    "gravedad_siniestro",
    "direccion",
    "barrio",
    "num_comuna",
    "nom_comuna",
    "codigo_comuna",
    "latitud",
    "longitud",
]

# Columnas originales de la capa que se descargan (codigo_comuna es derivada)
CAMPOS_ORIGEN_SINIESTROS = [
    "objectid",
    "radicado",
    "fecha_siniestro",
    "hora_siniestro",
    "dia",
    "mes",
    "anio",
    "clase_siniestro",
    "gravedad_siniestro",
    "direccion",
    "barrio",
    "num_comuna",
    "nom_comuna",
    "latitud",
    "longitud",
]


# -----------------------------------------------------------------------------
# Consultas a ArcGIS
# -----------------------------------------------------------------------------
def consultar_json(url, parametros):
    """GET con timeout y reintentos. ArcGIS responde HTTP 200 aun con error, por eso se revisa 'error'."""
    ultimo_error = None
    for numero_intento in range(1, NUMERO_INTENTOS + 1):
        try:
            respuesta = requests.get(url, params=parametros, timeout=SEGUNDOS_TIMEOUT)
            respuesta.raise_for_status()
            contenido = respuesta.json()
            if isinstance(contenido, dict) and "error" in contenido:
                raise RuntimeError("El servicio respondió con error: " + str(contenido["error"]))
            return contenido
        except Exception as error:
            ultimo_error = error
            registro.warning("Intento %d de %d falló: %s", numero_intento, NUMERO_INTENTOS, error)
            if numero_intento < NUMERO_INTENTOS:
                time.sleep(SEGUNDOS_ESPERA_ENTRE_INTENTOS)
    raise RuntimeError("No fue posible consultar " + url) from ultimo_error


def consultar_conteo_agrupado(url_capa, campos_agrupacion, filtro):
    """Cuenta registros agrupados por los campos indicados (outStatistics). Retorna lista de dicts."""
    estadisticas = [
        {
            "statisticType": "count",
            "onStatisticField": "objectid",
            "outStatisticFieldName": "conteo",
        }
    ]
    parametros = {
        "where": filtro,
        "outStatistics": json.dumps(estadisticas),
        "groupByFieldsForStatistics": campos_agrupacion,
        "f": "json",
    }
    respuesta = consultar_json(url_capa + "/query", parametros)
    if respuesta.get("exceededTransferLimit"):
        registro.warning("La consulta agrupada por %s superó el límite de registros; el resultado puede estar incompleto", campos_agrupacion)
    grupos = []
    for elemento in respuesta.get("features", []):
        grupos.append(elemento["attributes"])
    return grupos


def descargar_siniestros(url_capa):
    """Descarga los siniestros del filtro FILTRO_SINIESTROS_RDS paginando de 2000 en 2000."""
    total_esperado = consultar_json(
        url_capa + "/query",
        {"where": FILTRO_SINIESTROS_RDS, "returnCountOnly": "true", "f": "json"},
    )["count"]
    registro.info("Siniestros a descargar (%s): %d", FILTRO_SINIESTROS_RDS, total_esperado)

    filas = []
    desplazamiento = 0
    while True:
        parametros = {
            "where": FILTRO_SINIESTROS_RDS,
            "outFields": ",".join(CAMPOS_ORIGEN_SINIESTROS),
            "returnGeometry": "false",
            "orderByFields": "objectid",
            "resultOffset": desplazamiento,
            "resultRecordCount": TAMANO_PAGINA_ARCGIS,
            "f": "json",
        }
        respuesta = consultar_json(url_capa + "/query", parametros)
        elementos = respuesta.get("features", [])
        for elemento in elementos:
            filas.append(elemento["attributes"])
        registro.info("Descargados %d de %d siniestros", len(filas), total_esperado)
        if len(elementos) == 0:
            break
        desplazamiento = desplazamiento + len(elementos)
        if desplazamiento >= total_esperado:
            break

    if len(filas) != total_esperado:
        registro.warning("Se descargaron %d filas pero la capa reporta %d", len(filas), total_esperado)
    return filas


def leer_siniestros_csv_local():
    """Lee la copia local de siniestros (todo como texto; los vacíos quedan como None)."""
    tabla = pd.read_csv(ARCHIVO_CSV_SINIESTROS, dtype=str, keep_default_na=False, encoding="utf-8")
    filas = []
    for registro_csv in tabla.to_dict(orient="records"):
        fila = {}
        for nombre_columna, valor in registro_csv.items():
            if valor == "":
                fila[nombre_columna] = None
            else:
                fila[nombre_columna] = valor
        filas.append(fila)
    return filas


def guardar_siniestros_csv_local(filas):
    """Guarda la copia cruda de los siniestros descargados en datos_locales/."""
    ARCHIVO_CSV_SINIESTROS.parent.mkdir(parents=True, exist_ok=True)
    tabla = pd.DataFrame(filas, columns=CAMPOS_ORIGEN_SINIESTROS)
    tabla.to_csv(ARCHIVO_CSV_SINIESTROS, index=False, encoding="utf-8")
    registro.info("Copia local guardada en %s (%d filas)", ARCHIVO_CSV_SINIESTROS, len(tabla))


# -----------------------------------------------------------------------------
# Transformaciones
# -----------------------------------------------------------------------------
def es_vacio(valor):
    """True si el valor es None, NaN o texto vacío."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    if isinstance(valor, str) and valor.strip() == "":
        return True
    return False


def limpiar_texto(valor):
    """Quita espacios al inicio y final; retorna None si queda vacío."""
    if es_vacio(valor):
        return None
    return str(valor).strip()


def convertir_entero(valor):
    """Convierte 2019.0, '2019' o '2019.0' a entero. Retorna None si no es posible."""
    if es_vacio(valor):
        return None
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def convertir_decimal(valor, decimales):
    """Convierte a float redondeado. Retorna None si no es posible."""
    if es_vacio(valor):
        return None
    try:
        return round(float(valor), decimales)
    except (TypeError, ValueError):
        return None


def convertir_fecha(valor):
    """Convierte 'YYYY-MM-DD' a date. Retorna None si el formato no es válido."""
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def convertir_hora(valor):
    """Convierte 'HH:MM:SS' o 'HH:MM' a time. Retorna None si el formato no es válido."""
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    for formato in ["%H:%M:%S", "%H:%M"]:
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    return None


def extraer_codigo_comuna(num_comuna):
    """'Comuna 16' -> 16, 'Corregimiento 90' -> 90; ND, SN01, SN02 o vacío -> None."""
    texto = limpiar_texto(num_comuna)
    if texto is None:
        return None
    partes = texto.split()
    if len(partes) < 2:
        return None
    prefijo = partes[0].upper()
    numero = partes[-1]
    if prefijo not in ("COMUNA", "CORREGIMIENTO"):
        return None
    if not numero.isdigit():
        return None
    return int(numero)


def determinar_tipo_comuna(num_comuna):
    """Retorna 'COMUNA' o 'CORREGIMIENTO' según el prefijo de num_comuna."""
    texto = limpiar_texto(num_comuna)
    if texto is not None and texto.upper().startswith("CORREGIMIENTO"):
        return "CORREGIMIENTO"
    return "COMUNA"


def normalizar_nombre_comuna(nombre):
    """Mayúsculas, sin tildes, sin espacios repetidos y sin el prefijo 'CORREGIMIENTO DE'."""
    texto = limpiar_texto(nombre)
    if texto is None:
        return None
    texto_descompuesto = unicodedata.normalize("NFKD", texto.upper())
    caracteres_sin_tilde = []
    for caracter in texto_descompuesto:
        if not unicodedata.combining(caracter):
            caracteres_sin_tilde.append(caracter)
    texto_sin_tildes = "".join(caracteres_sin_tilde)
    palabras = texto_sin_tildes.split()
    texto_limpio = " ".join(palabras)
    prefijo = "CORREGIMIENTO DE "
    if texto_limpio.startswith(prefijo):
        texto_limpio = texto_limpio[len(prefijo):]
    return texto_limpio


def construir_catalogo_comunas(url_capa):
    """
    Retorna una lista de tuplas (codigo_comuna, nombre_comuna, nombre_normalizado, tipo).
    Si un mismo código aparece con varios nombres, se elige el más frecuente.
    """
    grupos = consultar_conteo_agrupado(url_capa, "num_comuna,nom_comuna", "1=1")
    mejor_por_codigo = {}
    for grupo in grupos:
        codigo = extraer_codigo_comuna(grupo.get("num_comuna"))
        if codigo is None:
            registro.info("Se omite del catálogo: num_comuna=%s, nom_comuna=%s", grupo.get("num_comuna"), grupo.get("nom_comuna"))
            continue
        conteo = grupo.get("conteo") or 0
        candidato = {
            "nombre_comuna": limpiar_texto(grupo.get("nom_comuna")),
            "tipo": determinar_tipo_comuna(grupo.get("num_comuna")),
            "conteo": conteo,
        }
        actual = mejor_por_codigo.get(codigo)
        if actual is None:
            mejor_por_codigo[codigo] = candidato
        else:
            registro.warning(
                "El código %d tiene varios nombres: '%s' (%d) y '%s' (%d)",
                codigo,
                actual["nombre_comuna"],
                actual["conteo"],
                candidato["nombre_comuna"],
                conteo,
            )
            if conteo > actual["conteo"]:
                mejor_por_codigo[codigo] = candidato

    catalogo = []
    for codigo in sorted(mejor_por_codigo.keys()):
        datos = mejor_por_codigo[codigo]
        nombre_normalizado = normalizar_nombre_comuna(datos["nombre_comuna"])
        catalogo.append((codigo, datos["nombre_comuna"], nombre_normalizado, datos["tipo"]))
    return catalogo


def construir_catalogo_barrios(url_capa, codigos_validos):
    """
    Retorna una lista ordenada de tuplas (nombre_barrio, codigo_comuna) sin repetidos.
    codigo_comuna es None si la comuna es ND/SN01/SN02/vacía o no está en el catálogo.
    """
    grupos = consultar_conteo_agrupado(url_capa, "barrio,num_comuna", "1=1")
    barrios_unicos = set()
    barrios_omitidos = 0
    for grupo in grupos:
        nombre_barrio = limpiar_texto(grupo.get("barrio"))
        if nombre_barrio is None:
            barrios_omitidos = barrios_omitidos + 1
            continue
        codigo = extraer_codigo_comuna(grupo.get("num_comuna"))
        if codigo is not None and codigo not in codigos_validos:
            codigo = None
        barrios_unicos.add((nombre_barrio, codigo))
    if barrios_omitidos > 0:
        registro.info("Grupos con barrio vacío omitidos del catálogo: %d", barrios_omitidos)
    lista_barrios = list(barrios_unicos)
    lista_barrios.sort(key=obtener_clave_orden_barrio)
    return lista_barrios


def obtener_clave_orden_barrio(barrio):
    """Ordena barrios por comuna (los sin comuna al final) y luego por nombre."""
    nombre_barrio = barrio[0]
    codigo = barrio[1]
    if codigo is None:
        return (1, 0, nombre_barrio)
    return (0, codigo, nombre_barrio)


def transformar_siniestros(filas_crudas, codigos_validos):
    """
    Convierte cada registro crudo en una tupla con el orden de COLUMNAS_SINIESTROS.
    Retorna (lista_de_tuplas, contadores_de_problemas).
    """
    filas_transformadas = []
    problemas = {
        "fecha_invalida": 0,
        "hora_invalida": 0,
        "codigo_comuna_null": 0,
        "codigo_fuera_de_catalogo": 0,
        "objectid_invalido": 0,
    }
    for fila in filas_crudas:
        objectid = convertir_entero(fila.get("objectid"))
        if objectid is None:
            problemas["objectid_invalido"] = problemas["objectid_invalido"] + 1
            continue

        fecha_siniestro = convertir_fecha(fila.get("fecha_siniestro"))
        if fecha_siniestro is None:
            problemas["fecha_invalida"] = problemas["fecha_invalida"] + 1

        hora_siniestro = convertir_hora(fila.get("hora_siniestro"))
        if hora_siniestro is None:
            problemas["hora_invalida"] = problemas["hora_invalida"] + 1

        codigo_comuna = extraer_codigo_comuna(fila.get("num_comuna"))
        if codigo_comuna is not None and codigo_comuna not in codigos_validos:
            problemas["codigo_fuera_de_catalogo"] = problemas["codigo_fuera_de_catalogo"] + 1
            codigo_comuna = None
        if codigo_comuna is None:
            problemas["codigo_comuna_null"] = problemas["codigo_comuna_null"] + 1

        fila_transformada = (
            objectid,
            convertir_entero(fila.get("radicado")),
            fecha_siniestro,
            hora_siniestro,
            limpiar_texto(fila.get("dia")),
            limpiar_texto(fila.get("mes")),
            convertir_entero(fila.get("anio")),
            limpiar_texto(fila.get("clase_siniestro")),
            limpiar_texto(fila.get("gravedad_siniestro")),
            limpiar_texto(fila.get("direccion")),
            limpiar_texto(fila.get("barrio")),
            limpiar_texto(fila.get("num_comuna")),
            limpiar_texto(fila.get("nom_comuna")),
            codigo_comuna,
            convertir_decimal(fila.get("latitud"), 7),
            convertir_decimal(fila.get("longitud"), 7),
        )
        filas_transformadas.append(fila_transformada)
    return filas_transformadas, problemas


# -----------------------------------------------------------------------------
# Base de datos
# -----------------------------------------------------------------------------
def conectar_base():
    """Abre la conexión a RDS MariaDB con los datos de .env."""
    conexion = pymysql.connect(
        host=os.environ["RDS_HOST"],
        port=int(os.environ.get("RDS_PUERTO", "3306")),
        user=os.environ["RDS_USUARIO"],
        password=os.environ["RDS_CLAVE"],
        database=os.environ["RDS_BASE"],
        charset="utf8mb4",
        connect_timeout=30,
        autocommit=False,
    )
    registro.info("Conectado a %s / base %s", os.environ["RDS_HOST"], os.environ["RDS_BASE"])
    return conexion


def aplicar_esquema(conexion):
    """Ejecuta cada sentencia de esquema.sql (separadas por ';', sin líneas de comentario)."""
    texto_esquema = ARCHIVO_ESQUEMA.read_text(encoding="utf-8")
    lineas_sin_comentarios = []
    for linea in texto_esquema.splitlines():
        if linea.strip().startswith("--"):
            continue
        lineas_sin_comentarios.append(linea)
    texto_limpio = "\n".join(lineas_sin_comentarios)
    sentencias = texto_limpio.split(";")
    with conexion.cursor() as cursor:
        for sentencia in sentencias:
            if sentencia.strip() == "":
                continue
            cursor.execute(sentencia)
    conexion.commit()
    registro.info("Esquema aplicado desde %s", ARCHIVO_ESQUEMA.name)


def cargar_comunas(conexion, catalogo_comunas):
    """Inserta o actualiza el catálogo de comunas."""
    sentencia = (
        "INSERT INTO comunas (codigo_comuna, nombre_comuna, nombre_normalizado, tipo) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "nombre_comuna = VALUES(nombre_comuna), "
        "nombre_normalizado = VALUES(nombre_normalizado), "
        "tipo = VALUES(tipo)"
    )
    with conexion.cursor() as cursor:
        cursor.executemany(sentencia, catalogo_comunas)
    conexion.commit()
    registro.info("Comunas cargadas: %d", len(catalogo_comunas))


def cargar_barrios(conexion, catalogo_barrios):
    """
    Inserta solo los barrios que aún no existen.
    No se usa ON DUPLICATE KEY porque el índice único no impide filas repetidas
    cuando codigo_comuna es NULL (en MariaDB varios NULL no chocan).
    """
    barrios_existentes = set()
    with conexion.cursor() as cursor:
        cursor.execute("SELECT nombre_barrio, codigo_comuna FROM barrios")
        for nombre_barrio, codigo_comuna in cursor.fetchall():
            barrios_existentes.add((nombre_barrio, codigo_comuna))

    barrios_nuevos = []
    for barrio in catalogo_barrios:
        if barrio not in barrios_existentes:
            barrios_nuevos.append(barrio)

    sentencia = "INSERT INTO barrios (nombre_barrio, codigo_comuna) VALUES (%s, %s)"
    with conexion.cursor() as cursor:
        cursor.executemany(sentencia, barrios_nuevos)
    conexion.commit()
    registro.info("Barrios en el catálogo: %d | nuevos insertados: %d", len(catalogo_barrios), len(barrios_nuevos))


def cargar_siniestros(conexion, filas_transformadas):
    """Inserta o actualiza los siniestros en lotes de TAMANO_LOTE_INSERCION."""
    nombres_columnas = ", ".join(COLUMNAS_SINIESTROS)
    marcadores = []
    for _ in COLUMNAS_SINIESTROS:
        marcadores.append("%s")
    actualizaciones = []
    for nombre_columna in COLUMNAS_SINIESTROS:
        if nombre_columna == "objectid":
            continue
        actualizaciones.append(nombre_columna + " = VALUES(" + nombre_columna + ")")
    sentencia = (
        "INSERT INTO siniestros (" + nombres_columnas + ") "
        "VALUES (" + ", ".join(marcadores) + ") "
        "ON DUPLICATE KEY UPDATE " + ", ".join(actualizaciones)
    )

    total_filas = len(filas_transformadas)
    with conexion.cursor() as cursor:
        for inicio_lote in range(0, total_filas, TAMANO_LOTE_INSERCION):
            fin_lote = inicio_lote + TAMANO_LOTE_INSERCION
            lote = filas_transformadas[inicio_lote:fin_lote]
            cursor.executemany(sentencia, lote)
            conexion.commit()
            registro.info("Siniestros cargados: %d de %d", min(fin_lote, total_filas), total_filas)


def consultar_filas(conexion, sentencia):
    """Ejecuta una consulta y retorna todas las filas."""
    with conexion.cursor() as cursor:
        cursor.execute(sentencia)
        return cursor.fetchall()


# -----------------------------------------------------------------------------
# Reportes
# -----------------------------------------------------------------------------
def reportar_conteos_por_anio(conteos_obtenidos, conteos_capa):
    """Compara los conteos por año contra la capa en vivo y contra la referencia del Módulo 1."""
    total_obtenido = 0
    todo_coincide = True
    registro.info("Año | obtenido | capa ArcGIS hoy | referencia Módulo 1")
    for anio in sorted(CONTEOS_REFERENCIA_MODULO1.keys()):
        obtenido = conteos_obtenidos.get(anio, 0)
        en_capa = conteos_capa.get(anio, 0)
        referencia = CONTEOS_REFERENCIA_MODULO1[anio]
        total_obtenido = total_obtenido + obtenido
        marca = "OK"
        if obtenido != en_capa:
            marca = "DIFERENTE A LA CAPA"
            todo_coincide = False
        elif obtenido != referencia:
            marca = "coincide con la capa; difiere de la referencia (la capa cambió)"
        registro.info("%d | %d | %d | %d  -> %s", anio, obtenido, en_capa, referencia, marca)
    registro.info("Total 2019-2022: %d (referencia Módulo 1: %d)", total_obtenido, sum(CONTEOS_REFERENCIA_MODULO1.values()))
    if not todo_coincide:
        registro.warning("Hay años cuyo conteo no coincide con la capa ArcGIS. Revise la descarga.")


def consultar_conteos_capa_por_anio(url_capa):
    """Conteo por año de la capa ArcGIS en vivo para el filtro de RDS."""
    grupos = consultar_conteo_agrupado(url_capa, "anio", FILTRO_SINIESTROS_RDS)
    conteos = {}
    for grupo in grupos:
        anio = convertir_entero(grupo.get("anio"))
        conteos[anio] = grupo.get("conteo")
    return conteos


def reportar_desde_memoria(filas_transformadas, catalogo_comunas, catalogo_barrios, conteos_capa):
    """Reporte equivalente al de la base, calculado sobre los datos transformados (modo --solo-descarga)."""
    registro.info("=== Reporte (modo solo descarga, sin base de datos) ===")
    registro.info("comunas: %d | barrios: %d | siniestros: %d", len(catalogo_comunas), len(catalogo_barrios), len(filas_transformadas))

    posicion_anio = COLUMNAS_SINIESTROS.index("anio")
    posicion_radicado = COLUMNAS_SINIESTROS.index("radicado")
    posicion_codigo = COLUMNAS_SINIESTROS.index("codigo_comuna")
    conteos_por_anio = {}
    conteos_por_radicado = {}
    siniestros_sin_comuna = 0
    for fila in filas_transformadas:
        anio = fila[posicion_anio]
        conteos_por_anio[anio] = conteos_por_anio.get(anio, 0) + 1
        radicado = fila[posicion_radicado]
        conteos_por_radicado[radicado] = conteos_por_radicado.get(radicado, 0) + 1
        if fila[posicion_codigo] is None:
            siniestros_sin_comuna = siniestros_sin_comuna + 1
    reportar_conteos_por_anio(conteos_por_anio, conteos_capa)

    radicados_duplicados = 0
    filas_sobrantes = 0
    for radicado, conteo in conteos_por_radicado.items():
        if conteo > 1:
            radicados_duplicados = radicados_duplicados + 1
            filas_sobrantes = filas_sobrantes + conteo - 1
    registro.info("Radicados duplicados: %d (filas sobrantes: %d)", radicados_duplicados, filas_sobrantes)
    registro.info("Siniestros con codigo_comuna NULL: %d", siniestros_sin_comuna)


def reportar_desde_base(conexion, conteos_capa):
    """Reporte final consultando la base de datos."""
    registro.info("=== Reporte final desde RDS ===")
    for nombre_tabla in ["comunas", "barrios", "siniestros"]:
        filas = consultar_filas(conexion, "SELECT COUNT(*) FROM " + nombre_tabla)
        registro.info("Filas en %s: %d", nombre_tabla, filas[0][0])

    conteos_por_anio = {}
    for anio, conteo in consultar_filas(conexion, "SELECT anio, COUNT(*) FROM siniestros GROUP BY anio ORDER BY anio"):
        conteos_por_anio[anio] = conteo
    reportar_conteos_por_anio(conteos_por_anio, conteos_capa)

    duplicados = consultar_filas(
        conexion,
        "SELECT COUNT(*), COALESCE(SUM(repeticiones - 1), 0) FROM ("
        "  SELECT radicado, COUNT(*) AS repeticiones FROM siniestros"
        "  GROUP BY radicado HAVING COUNT(*) > 1"
        ") AS radicados_repetidos",
    )
    registro.info("Radicados duplicados: %d (filas sobrantes: %d)", duplicados[0][0], duplicados[0][1])

    sin_comuna = consultar_filas(conexion, "SELECT COUNT(*) FROM siniestros WHERE codigo_comuna IS NULL")
    registro.info("Siniestros con codigo_comuna NULL: %d", sin_comuna[0][0])


# -----------------------------------------------------------------------------
# Programa principal
# -----------------------------------------------------------------------------
def leer_argumentos():
    analizador = argparse.ArgumentParser(description="Carga la base movilidad en RDS MariaDB.")
    analizador.add_argument("--solo-descarga", action="store_true", help="No se conecta a la base; solo descarga, transforma y reporta.")
    analizador.add_argument("--usar-csv-local", action="store_true", help="Usa la copia local de siniestros en vez de descargarlos.")
    return analizador.parse_args()


def main():
    load_dotenv()
    argumentos = leer_argumentos()
    url_capa = os.getenv("URL_ARCGIS_ACCIDENTES") or URL_ACCIDENTES_POR_DEFECTO

    # 1. Catálogos (consultas agregadas sobre todos los años)
    catalogo_comunas = construir_catalogo_comunas(url_capa)
    codigos_validos = set()
    for comuna in catalogo_comunas:
        codigos_validos.add(comuna[0])
        registro.info("Comuna %d: %s -> %s (%s)", comuna[0], comuna[1], comuna[2], comuna[3])
    catalogo_barrios = construir_catalogo_barrios(url_capa, codigos_validos)
    registro.info("Catálogo de barrios: %d combinaciones barrio-comuna", len(catalogo_barrios))

    # 2. Siniestros 2019-2022
    if argumentos.usar_csv_local:
        if not ARCHIVO_CSV_SINIESTROS.exists():
            raise FileNotFoundError("No existe " + str(ARCHIVO_CSV_SINIESTROS) + "; ejecute sin --usar-csv-local")
        registro.info("Leyendo siniestros desde %s", ARCHIVO_CSV_SINIESTROS)
        filas_crudas = leer_siniestros_csv_local()
    else:
        filas_crudas = descargar_siniestros(url_capa)
        guardar_siniestros_csv_local(filas_crudas)

    filas_transformadas, problemas = transformar_siniestros(filas_crudas, codigos_validos)
    registro.info("Siniestros transformados: %d | problemas: %s", len(filas_transformadas), problemas)
    conteos_capa = consultar_conteos_capa_por_anio(url_capa)

    if argumentos.solo_descarga:
        reportar_desde_memoria(filas_transformadas, catalogo_comunas, catalogo_barrios, conteos_capa)
        return

    # 3. Carga en RDS
    conexion = conectar_base()
    try:
        aplicar_esquema(conexion)
        cargar_comunas(conexion, catalogo_comunas)
        cargar_barrios(conexion, catalogo_barrios)
        cargar_siniestros(conexion, filas_transformadas)
        reportar_desde_base(conexion, conteos_capa)
    finally:
        conexion.close()
    registro.info("Carga de RDS terminada")


if __name__ == "__main__":
    main()
