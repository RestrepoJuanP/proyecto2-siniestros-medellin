"""
Exploración de la API archive de Open-Meteo para Medellín (2019-2025).

Pasos:
1. Consulta clima horario (temperatura, precipitación, lluvia, humedad relativa)
   y diario (precipitación total, temperatura media y máxima).
2. Reporta cantidad de registros horarios y diarios y nulos por variable.
3. Cuenta, por año, los días con precipitación diaria > 10 mm.
4. Guarda datos_locales/clima_horario.csv y datos_locales/clima_diario.csv.

Los hallazgos se registran en consola y en hallazgos.md (sección "clima_openmeteo").
"""

import logging

import pandas as pd
from dotenv import load_dotenv

from utilidades_exploracion import (
    asegurar_carpeta_datos_locales,
    construir_tabla_markdown,
    consultar_json,
    escribir_seccion_hallazgos,
    leer_variable_entorno,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
registro = logging.getLogger(__name__)

URL_POR_DEFECTO = "https://archive-api.open-meteo.com/v1/archive"

# Parámetros del caso de estudio: centro de Medellín, periodo 2019-2025
LATITUD_MEDELLIN = 6.2442
LONGITUD_MEDELLIN = -75.5812
FECHA_INICIO = "2019-01-01"
FECHA_FIN = "2025-12-31"
ZONA_HORARIA = "America/Bogota"
VARIABLES_HORARIAS = ["temperature_2m", "precipitation", "rain", "relative_humidity_2m"]
VARIABLES_DIARIAS = ["precipitation_sum", "temperature_2m_mean", "temperature_2m_max"]
UMBRAL_LLUVIA_FUERTE_MM = 10.0


def consultar_clima(url_api):
    """Consulta la API archive de Open-Meteo y retorna el JSON completo."""
    parametros = {
        "latitude": LATITUD_MEDELLIN,
        "longitude": LONGITUD_MEDELLIN,
        "start_date": FECHA_INICIO,
        "end_date": FECHA_FIN,
        "timezone": ZONA_HORARIA,
        "hourly": ",".join(VARIABLES_HORARIAS),
        "daily": ",".join(VARIABLES_DIARIAS),
    }
    return consultar_json(url_api, parametros)


def convertir_bloque_a_tabla(bloque):
    """Convierte el bloque 'hourly' o 'daily' de Open-Meteo (dict de listas) en un DataFrame."""
    tabla = pd.DataFrame(bloque)
    tabla["time"] = pd.to_datetime(tabla["time"])
    return tabla


def contar_nulos(tabla, variables, unidades):
    """Retorna una lista de (variable, unidad, nulos, % nulos) para las variables indicadas."""
    resultado = []
    total_filas = len(tabla)
    for variable in variables:
        cantidad_nulos = int(tabla[variable].isna().sum())
        porcentaje = 0.0
        if total_filas > 0:
            porcentaje = round(100.0 * cantidad_nulos / total_filas, 2)
        resultado.append((variable, unidades.get(variable, ""), cantidad_nulos, porcentaje))
    return resultado


def resumir_variables(tabla, variables):
    """Retorna (variable, mínimo, promedio, máximo) para cada variable numérica."""
    resultado = []
    for variable in variables:
        columna = tabla[variable]
        resultado.append((variable, columna.min(), round(columna.mean(), 2), columna.max()))
    return resultado


def contar_dias_lluvia_fuerte_por_anio(tabla_diaria):
    """Cuenta por año los días con precipitation_sum mayor al umbral."""
    tabla_diaria = tabla_diaria.copy()
    tabla_diaria["anio"] = tabla_diaria["time"].dt.year
    tabla_diaria["es_lluvia_fuerte"] = tabla_diaria["precipitation_sum"] > UMBRAL_LLUVIA_FUERTE_MM
    tabla_diaria["tiene_lluvia"] = tabla_diaria["precipitation_sum"] > 0
    resultado = []
    for anio, grupo in tabla_diaria.groupby("anio"):
        dias_totales = len(grupo)
        dias_con_lluvia = int(grupo["tiene_lluvia"].sum())
        dias_lluvia_fuerte = int(grupo["es_lluvia_fuerte"].sum())
        precipitacion_total = round(float(grupo["precipitation_sum"].sum()), 1)
        resultado.append((int(anio), dias_totales, dias_con_lluvia, dias_lluvia_fuerte, precipitacion_total))
    return resultado


def main():
    load_dotenv()
    url_api = leer_variable_entorno("URL_OPENMETEO_ARCHIVO", URL_POR_DEFECTO)
    carpeta_datos = asegurar_carpeta_datos_locales()

    registro.info("Consultando Open-Meteo de %s a %s", FECHA_INICIO, FECHA_FIN)
    respuesta = consultar_clima(url_api)

    tabla_horaria = convertir_bloque_a_tabla(respuesta["hourly"])
    tabla_diaria = convertir_bloque_a_tabla(respuesta["daily"])
    unidades_horarias = respuesta.get("hourly_units", {})
    unidades_diarias = respuesta.get("daily_units", {})

    ruta_horaria = carpeta_datos / "clima_horario.csv"
    ruta_diaria = carpeta_datos / "clima_diario.csv"
    tabla_horaria.to_csv(ruta_horaria, index=False, encoding="utf-8")
    tabla_diaria.to_csv(ruta_diaria, index=False, encoding="utf-8")
    registro.info("Guardados %s y %s", ruta_horaria, ruta_diaria)

    cantidad_horas = len(tabla_horaria)
    cantidad_dias = len(tabla_diaria)
    registro.info("Registros horarios: %d | Registros diarios: %d", cantidad_horas, cantidad_dias)
    registro.info(
        "Coordenadas devueltas por la API: lat %s, lon %s, elevación %s m",
        respuesta.get("latitude"),
        respuesta.get("longitude"),
        respuesta.get("elevation"),
    )

    nulos_horarios = contar_nulos(tabla_horaria, VARIABLES_HORARIAS, unidades_horarias)
    nulos_diarios = contar_nulos(tabla_diaria, VARIABLES_DIARIAS, unidades_diarias)
    for variable, _unidad, cantidad_nulos, porcentaje in nulos_horarios + nulos_diarios:
        registro.info("Variable %s: %d nulos (%.2f%%)", variable, cantidad_nulos, porcentaje)

    resumen_horario = resumir_variables(tabla_horaria, VARIABLES_HORARIAS)
    resumen_diario = resumir_variables(tabla_diaria, VARIABLES_DIARIAS)

    dias_lluvia_por_anio = contar_dias_lluvia_fuerte_por_anio(tabla_diaria)
    for anio, dias_totales, dias_con_lluvia, dias_lluvia_fuerte, precipitacion_total in dias_lluvia_por_anio:
        registro.info(
            "Año %d: %d días, %d con lluvia, %d con > %.0f mm, %.1f mm totales",
            anio,
            dias_totales,
            dias_con_lluvia,
            dias_lluvia_fuerte,
            UMBRAL_LLUVIA_FUERTE_MM,
            precipitacion_total,
        )

    # Comparar precipitation vs rain (en Medellín no nieva: deberían coincidir)
    diferencia_lluvia = (tabla_horaria["precipitation"] - tabla_horaria["rain"]).abs()
    horas_con_diferencia = int((diferencia_lluvia > 0.001).sum())
    horas_con_lluvia = int((tabla_horaria["precipitation"] > 0).sum())
    registro.info("Horas con precipitación > 0: %d; horas donde precipitation != rain: %d", horas_con_lluvia, horas_con_diferencia)

    # Construir sección Markdown
    secciones = []
    secciones.append("## 2. Clima — API archive de Open-Meteo\n")
    secciones.append(
        "Fuente: " + url_api + " — Medellín (lat " + str(LATITUD_MEDELLIN) + ", lon " + str(LONGITUD_MEDELLIN)
        + "), " + FECHA_INICIO + " a " + FECHA_FIN + ", zona horaria `" + ZONA_HORARIA + "`.\n"
    )
    secciones.append(
        "La API ajusta a la celda de su malla: lat **" + str(respuesta.get("latitude")) + "**, lon **"
        + str(respuesta.get("longitude")) + "**, elevación **" + str(respuesta.get("elevation")) + " m**. "
        "Una sola petición devuelve los 7 años (no requiere paginación).\n"
    )
    secciones.append("### Cantidad de registros\n")
    secciones.append(
        construir_tabla_markdown(
            ["Granularidad", "Registros", "Desde", "Hasta"],
            [
                ["Horaria", cantidad_horas, str(tabla_horaria["time"].min()), str(tabla_horaria["time"].max())],
                ["Diaria", cantidad_dias, str(tabla_diaria["time"].min().date()), str(tabla_diaria["time"].max().date())],
            ],
        )
        + "\n"
    )
    secciones.append("### Nulos por variable\n")
    secciones.append(
        construir_tabla_markdown(["Variable horaria", "Unidad", "Nulos", "% nulos"], nulos_horarios) + "\n"
    )
    secciones.append(
        construir_tabla_markdown(["Variable diaria", "Unidad", "Nulos", "% nulos"], nulos_diarios) + "\n"
    )
    secciones.append("### Rango de valores\n")
    secciones.append(construir_tabla_markdown(["Variable horaria", "Mínimo", "Promedio", "Máximo"], resumen_horario) + "\n")
    secciones.append(construir_tabla_markdown(["Variable diaria", "Mínimo", "Promedio", "Máximo"], resumen_diario) + "\n")
    secciones.append(
        "- Horas con precipitación > 0: **" + str(horas_con_lluvia) + "** de " + str(cantidad_horas) + ".\n"
        "- Horas donde `precipitation` ≠ `rain`: **" + str(horas_con_diferencia) + "**.\n"
    )
    secciones.append("### Días con precipitación diaria > " + str(int(UMBRAL_LLUVIA_FUERTE_MM)) + " mm por año\n")
    secciones.append(
        construir_tabla_markdown(
            ["Año", "Días", "Días con lluvia (> 0 mm)", "Días > 10 mm", "Precipitación total (mm)"],
            dias_lluvia_por_anio,
        )
        + "\n"
    )
    secciones.append("Archivos generados: `datos_locales/clima_horario.csv`, `datos_locales/clima_diario.csv`.\n")

    escribir_seccion_hallazgos("clima_openmeteo", "\n".join(secciones))
    registro.info("Exploración de clima terminada")


if __name__ == "__main__":
    main()
