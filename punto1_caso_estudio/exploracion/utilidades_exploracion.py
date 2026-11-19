"""
Utilidades compartidas por los scripts de exploración del Punto 1.

Incluye:
- Consultas HTTP con timeout y reintentos simples.
- Construcción de tablas en formato Markdown (sin dependencias externas).
- Escritura de secciones en hallazgos.md (reemplaza la sección si ya existe,
  para que volver a correr un script no duplique resultados).
"""

import logging
import os
import time
import unicodedata
from pathlib import Path

import requests

registro = logging.getLogger(__name__)

# Rutas base del proyecto
CARPETA_EXPLORACION = Path(__file__).resolve().parent
CARPETA_RAIZ_PROYECTO = CARPETA_EXPLORACION.parent.parent
CARPETA_DATOS_LOCALES = CARPETA_RAIZ_PROYECTO / "datos_locales"
ARCHIVO_HALLAZGOS = CARPETA_EXPLORACION / "hallazgos.md"

NUMERO_INTENTOS = 3
SEGUNDOS_ESPERA_ENTRE_INTENTOS = 5
SEGUNDOS_TIMEOUT = 120


def asegurar_carpeta_datos_locales():
    """Crea la carpeta datos_locales/ si no existe y la retorna."""
    CARPETA_DATOS_LOCALES.mkdir(parents=True, exist_ok=True)
    return CARPETA_DATOS_LOCALES


def consultar_json(url, parametros):
    """
    Hace un GET y retorna el JSON de la respuesta.
    Reintenta hasta NUMERO_INTENTOS veces si hay error de red, código HTTP
    de error o si ArcGIS responde con un objeto "error" dentro del JSON.
    """
    ultimo_error = None
    for numero_intento in range(1, NUMERO_INTENTOS + 1):
        try:
            respuesta = requests.get(url, params=parametros, timeout=SEGUNDOS_TIMEOUT)
            respuesta.raise_for_status()
            contenido = respuesta.json()
            # ArcGIS devuelve HTTP 200 aun cuando la consulta falla
            if isinstance(contenido, dict) and "error" in contenido:
                raise RuntimeError("El servicio respondió con error: " + str(contenido["error"]))
            return contenido
        except Exception as error:
            ultimo_error = error
            registro.warning(
                "Intento %d de %d falló para %s: %s",
                numero_intento,
                NUMERO_INTENTOS,
                url,
                error,
            )
            if numero_intento < NUMERO_INTENTOS:
                time.sleep(SEGUNDOS_ESPERA_ENTRE_INTENTOS)
    raise RuntimeError("No fue posible consultar " + url + " después de varios intentos") from ultimo_error


def formatear_valor(valor):
    """Convierte un valor a texto apto para una celda de tabla Markdown."""
    if valor is None:
        return "(nulo)"
    if isinstance(valor, float):
        if valor.is_integer():
            return str(int(valor))
        return f"{valor:.2f}"
    texto = str(valor)
    texto = texto.replace("|", "\\|")
    texto = texto.replace("\n", " ")
    if texto == "":
        return "(vacío)"
    return texto


def construir_tabla_markdown(encabezados, filas):
    """Construye una tabla Markdown a partir de una lista de encabezados y una lista de filas."""
    lineas = []
    lineas.append("| " + " | ".join(encabezados) + " |")
    separadores = []
    for _ in encabezados:
        separadores.append("---")
    lineas.append("| " + " | ".join(separadores) + " |")
    for fila in filas:
        celdas = []
        for valor in fila:
            celdas.append(formatear_valor(valor))
        lineas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(lineas)


def escribir_seccion_hallazgos(identificador_seccion, contenido_markdown):
    """
    Escribe (o reemplaza) una sección en hallazgos.md delimitada por marcadores HTML.
    Así cada script mantiene su propia sección sin pisar las de los demás.
    """
    marcador_inicio = "<!-- inicio:" + identificador_seccion + " -->"
    marcador_fin = "<!-- fin:" + identificador_seccion + " -->"
    bloque_nuevo = marcador_inicio + "\n" + contenido_markdown.strip() + "\n" + marcador_fin + "\n"

    if ARCHIVO_HALLAZGOS.exists():
        texto_actual = ARCHIVO_HALLAZGOS.read_text(encoding="utf-8")
    else:
        texto_actual = (
            "# Hallazgos de la exploración de fuentes (Punto 1)\n\n"
            "Archivo generado automáticamente por los scripts de `punto1_caso_estudio/exploracion/`.\n"
            "Cada sección se reemplaza al volver a ejecutar su script.\n\n"
        )

    posicion_inicio = texto_actual.find(marcador_inicio)
    posicion_fin = texto_actual.find(marcador_fin)
    if posicion_inicio != -1 and posicion_fin != -1:
        posicion_fin_completa = posicion_fin + len(marcador_fin)
        # Consumir el salto de línea que sigue al marcador de fin, si existe
        if texto_actual[posicion_fin_completa:posicion_fin_completa + 1] == "\n":
            posicion_fin_completa = posicion_fin_completa + 1
        texto_nuevo = texto_actual[:posicion_inicio] + bloque_nuevo + texto_actual[posicion_fin_completa:]
    else:
        if not texto_actual.endswith("\n"):
            texto_actual = texto_actual + "\n"
        texto_nuevo = texto_actual + "\n" + bloque_nuevo

    ARCHIVO_HALLAZGOS.write_text(texto_nuevo, encoding="utf-8")
    registro.info("Sección '%s' escrita en %s", identificador_seccion, ARCHIVO_HALLAZGOS)


def normalizar_nombre(texto):
    """
    Normaliza un nombre para compararlo: minúsculas, sin tildes, sin espacios extra
    y sin el prefijo 'corregimiento de'.
    """
    if texto is None:
        return ""
    texto_minusculas = str(texto).strip().lower()
    texto_descompuesto = unicodedata.normalize("NFKD", texto_minusculas)
    caracteres_sin_tilde = []
    for caracter in texto_descompuesto:
        if not unicodedata.combining(caracter):
            caracteres_sin_tilde.append(caracter)
    texto_sin_tildes = "".join(caracteres_sin_tilde)
    prefijo = "corregimiento de "
    if texto_sin_tildes.startswith(prefijo):
        texto_sin_tildes = texto_sin_tildes[len(prefijo):]
    palabras = texto_sin_tildes.split()
    return " ".join(palabras)


def leer_variable_entorno(nombre_variable, valor_por_defecto):
    """Lee una variable de entorno; si no está definida usa el valor por defecto documentado en .env.example."""
    valor = os.getenv(nombre_variable)
    if valor is None or valor.strip() == "":
        return valor_por_defecto
    return valor.strip()
