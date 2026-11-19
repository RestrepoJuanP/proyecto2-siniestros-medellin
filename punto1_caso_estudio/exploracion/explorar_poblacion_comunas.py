"""
Exploración de la capa ArcGIS "VC_Distribucion_Poblacional" (proyección de población
por comuna y corregimiento de Medellín).

Pasos:
1. Metadatos de la capa: campos y tipos.
2. Descarga de todos los registros sin geometría -> datos_locales/poblacion_comunas_raw.csv
3. Identificación de columnas de comuna y de población por año.
4. Verificación del cruce con num_comuna / nom_comuna de la capa de siniestros
   (VM_Accidentes), reportando los valores que no coinciden.

Los hallazgos se registran en consola y en hallazgos.md (sección "poblacion_comunas").
"""

import json
import logging

import pandas as pd
from dotenv import load_dotenv

from utilidades_exploracion import (
    asegurar_carpeta_datos_locales,
    construir_tabla_markdown,
    consultar_json,
    escribir_seccion_hallazgos,
    leer_variable_entorno,
    normalizar_nombre,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
registro = logging.getLogger(__name__)

URL_POBLACION_POR_DEFECTO = (
    "https://www.medellin.gov.co/servidormapas/rest/services/mapas_nacionales/VC_Distribucion_Poblacional/MapServer/1"
)
URL_ACCIDENTES_POR_DEFECTO = (
    "https://www.medellin.gov.co/servidormapas/rest/services/transporte/VM_Accidentes/MapServer/0"
)
TAMANO_PAGINA = 1000


def consultar_campos(url_capa):
    """Retorna la lista de campos (nombre, tipo, alias) y el nombre de la capa."""
    metadatos = consultar_json(url_capa, {"f": "json"})
    campos = []
    for campo in metadatos.get("fields", []):
        campos.append((campo["name"], campo["type"], campo.get("alias", "")))
    return campos, metadatos.get("name")


def descargar_todos_los_registros(url_capa):
    """Descarga todos los registros de la capa, paginando con resultOffset, sin geometría."""
    filas = []
    desplazamiento = 0
    while True:
        parametros = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "objectid",
            "resultOffset": desplazamiento,
            "resultRecordCount": TAMANO_PAGINA,
            "f": "json",
        }
        respuesta = consultar_json(url_capa + "/query", parametros)
        elementos = respuesta.get("features", [])
        for elemento in elementos:
            filas.append(elemento["attributes"])
        registro.info("Página con desplazamiento %d: %d registros", desplazamiento, len(elementos))
        hay_mas = respuesta.get("exceededTransferLimit", False)
        if len(elementos) == 0 or not hay_mas:
            break
        desplazamiento = desplazamiento + len(elementos)
    return pd.DataFrame(filas)


def consultar_comunas_de_siniestros(url_accidentes):
    """Retorna las combinaciones distintas (num_comuna, nom_comuna, conteo) de la capa de siniestros."""
    estadisticas = [
        {
            "statisticType": "count",
            "onStatisticField": "objectid",
            "outStatisticFieldName": "conteo",
        }
    ]
    parametros = {
        "where": "1=1",
        "outStatistics": json.dumps(estadisticas),
        "groupByFieldsForStatistics": "num_comuna,nom_comuna",
        "f": "json",
    }
    respuesta = consultar_json(url_accidentes + "/query", parametros)
    combinaciones = []
    for elemento in respuesta.get("features", []):
        atributos = elemento["attributes"]
        combinaciones.append((atributos.get("num_comuna"), atributos.get("nom_comuna"), atributos.get("conteo")))
    return combinaciones


def extraer_codigo_numerico(num_comuna):
    """Extrae el número de 'Comuna 16' o 'Corregimiento 90'. Retorna None si no hay número."""
    if num_comuna is None:
        return None
    partes = str(num_comuna).split()
    if len(partes) == 0:
        return None
    ultima_parte = partes[-1]
    if ultima_parte.isdigit():
        return int(ultima_parte)
    return None


def obtener_clave_orden_cruce(fila):
    """Ordena por código numérico (comunas y luego corregimientos); los sin código van al final."""
    codigo = fila[3]
    if codigo is None:
        return (1, 0, str(fila[0]))
    return (0, codigo, str(fila[0]))


def main():
    load_dotenv()
    url_poblacion = leer_variable_entorno("URL_ARCGIS_POBLACION", URL_POBLACION_POR_DEFECTO)
    url_accidentes = leer_variable_entorno("URL_ARCGIS_ACCIDENTES", URL_ACCIDENTES_POR_DEFECTO)
    carpeta_datos = asegurar_carpeta_datos_locales()

    # 1. Metadatos
    campos, nombre_capa = consultar_campos(url_poblacion)
    for nombre_campo, tipo_campo, _alias in campos:
        registro.info("Campo: %s (%s)", nombre_campo, tipo_campo)

    # 2. Descarga completa
    tabla_poblacion = descargar_todos_los_registros(url_poblacion)
    ruta_salida = carpeta_datos / "poblacion_comunas_raw.csv"
    tabla_poblacion.to_csv(ruta_salida, index=False, encoding="utf-8")
    registro.info("Guardados %d registros en %s", len(tabla_poblacion), ruta_salida)

    # 3. Identificar columnas
    columnas_poblacion = []
    columnas_nombre = []
    for nombre_campo, tipo_campo, _alias in campos:
        if nombre_campo.startswith("total_"):
            columnas_poblacion.append(nombre_campo)
        elif tipo_campo == "esriFieldTypeString":
            columnas_nombre.append(nombre_campo)
    registro.info("Columnas con nombre de comuna: %s", columnas_nombre)
    registro.info("Columnas de población por año: %s", columnas_poblacion)

    columnas_para_mostrar = ["objectid", "nombre", "total_2019", "total_2022", "total_2025"]
    tabla_ordenada = tabla_poblacion.sort_values("objectid")
    filas_poblacion = tabla_ordenada[columnas_para_mostrar].values.tolist()
    suma_2019 = int(tabla_poblacion["total_2019"].sum())
    suma_2025 = int(tabla_poblacion["total_2025"].sum())
    registro.info("Población total Medellín: 2019 = %d, 2025 = %d", suma_2019, suma_2025)

    # 4. Cruce con siniestros
    combinaciones_siniestros = consultar_comunas_de_siniestros(url_accidentes)
    nombres_poblacion_normalizados = {}
    for nombre_original in tabla_poblacion["nombre"]:
        nombres_poblacion_normalizados[normalizar_nombre(nombre_original)] = nombre_original

    filas_cruce = []
    nombres_siniestros_normalizados = set()
    for num_comuna, nom_comuna, conteo in combinaciones_siniestros:
        nombre_normalizado = normalizar_nombre(nom_comuna)
        nombres_siniestros_normalizados.add(nombre_normalizado)
        nombre_en_poblacion = nombres_poblacion_normalizados.get(nombre_normalizado)
        coincide_exacto = nombre_en_poblacion is not None and nombre_en_poblacion == nom_comuna
        if nombre_en_poblacion is None:
            estado = "NO coincide"
        elif coincide_exacto:
            estado = "Exacto"
        else:
            estado = "Coincide tras normalizar"
        filas_cruce.append(
            (num_comuna, nom_comuna, conteo, extraer_codigo_numerico(num_comuna), nombre_en_poblacion, estado)
        )
    filas_cruce.sort(key=obtener_clave_orden_cruce)

    for fila in filas_cruce:
        registro.info("Siniestros %s / %s (%s) -> población: %s [%s]", fila[0], fila[1], fila[2], fila[4], fila[5])

    nombres_sin_siniestros = []
    for nombre_normalizado, nombre_original in nombres_poblacion_normalizados.items():
        if nombre_normalizado not in nombres_siniestros_normalizados:
            nombres_sin_siniestros.append(nombre_original)
    registro.info("Nombres de la capa de población sin equivalente en siniestros: %s", nombres_sin_siniestros)

    registros_sin_comuna = 0
    for fila in filas_cruce:
        if fila[5] == "NO coincide":
            registros_sin_comuna = registros_sin_comuna + fila[2]

    # Construir sección Markdown
    secciones = []
    secciones.append("## 3. Población por comuna — capa ArcGIS `VC_Distribucion_Poblacional`\n")
    secciones.append("Fuente: " + url_poblacion + "\n")
    secciones.append("### Campos y tipos\n")
    secciones.append("Nombre de la capa: **" + str(nombre_capa) + "**.\n")
    secciones.append(construir_tabla_markdown(["Campo", "Tipo ArcGIS", "Alias"], campos) + "\n")
    secciones.append("### Columnas identificadas\n")
    secciones.append(
        "- Nombre de comuna/corregimiento: `" + "`, `".join(columnas_nombre) + "` (no existe columna de código).\n"
        "- Población por año: `" + "`, `".join(columnas_poblacion) + "` (proyección, formato ancho: una columna por año).\n"
        "- Registros descargados: **" + str(len(tabla_poblacion)) + "** en `datos_locales/poblacion_comunas_raw.csv`.\n"
        "- Población total (suma de filas): 2019 = **" + f"{suma_2019:,}" + "**, 2025 = **" + f"{suma_2025:,}" + "**.\n"
    )
    secciones.append(
        construir_tabla_markdown(["objectid", "nombre", "total_2019", "total_2022", "total_2025"], filas_poblacion) + "\n"
    )
    secciones.append("### Cruce con `num_comuna` / `nom_comuna` de siniestros\n")
    secciones.append(
        "Comparación por nombre normalizado (minúsculas, sin tildes, sin el prefijo \"Corregimiento de\").\n"
    )
    secciones.append(
        construir_tabla_markdown(
            ["num_comuna (siniestros)", "nom_comuna (siniestros)", "Siniestros", "Código extraído", "nombre (población)", "Resultado"],
            filas_cruce,
        )
        + "\n"
    )
    if len(nombres_sin_siniestros) > 0:
        secciones.append("Nombres de población sin equivalente en siniestros: `" + "`, `".join(nombres_sin_siniestros) + "`.\n")
    else:
        secciones.append("Todos los nombres de la capa de población tienen equivalente en siniestros.\n")
    secciones.append(
        "Siniestros cuyo `nom_comuna` no cruza con la población: **" + f"{registros_sin_comuna:,}" + "**.\n"
    )

    escribir_seccion_hallazgos("poblacion_comunas", "\n".join(secciones))
    registro.info("Exploración de población terminada")


if __name__ == "__main__":
    main()
