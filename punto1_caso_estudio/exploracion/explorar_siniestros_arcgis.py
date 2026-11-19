"""
Exploración de la capa ArcGIS "VM_Accidentes" (siniestralidad vial de Medellín).

Pasos:
1. Metadatos de la capa: campos y tipos.
2. Total de registros.
3. Conteo de registros por año.
4. Valores distintos (con conteo) de gravedad_siniestro, clase_siniestro, dia y nom_comuna.
5. Descarga de una muestra de 2000 registros -> datos_locales/muestra_siniestros.csv
6. Análisis de la muestra: formato de fecha/hora, nulos por columna y coordenadas fuera de Medellín.

Los hallazgos se registran en consola y en hallazgos.md (sección "siniestros_arcgis").
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
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
registro = logging.getLogger(__name__)

URL_POR_DEFECTO = "https://www.medellin.gov.co/servidormapas/rest/services/transporte/VM_Accidentes/MapServer/0"
TAMANO_MUESTRA = 2000
CAMPOS_PARA_VALORES_DISTINTOS = ["gravedad_siniestro", "clase_siniestro", "dia", "nom_comuna"]

# Rango aproximado de coordenadas de Medellín
LATITUD_MINIMA = 6.1
LATITUD_MAXIMA = 6.4
LONGITUD_MINIMA = -75.7
LONGITUD_MAXIMA = -75.4


def consultar_metadatos(url_capa):
    """Retorna la lista de campos (nombre, tipo, alias) y datos generales de la capa."""
    metadatos = consultar_json(url_capa, {"f": "json"})
    campos = []
    for campo in metadatos.get("fields", []):
        campos.append((campo["name"], campo["type"], campo.get("alias", "")))
    datos_generales = {
        "nombre_capa": metadatos.get("name"),
        "maximo_registros_por_consulta": metadatos.get("maxRecordCount"),
    }
    return campos, datos_generales


def consultar_total_registros(url_capa):
    """Cuenta el total de registros de la capa."""
    parametros = {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    respuesta = consultar_json(url_capa + "/query", parametros)
    return respuesta["count"]


def contar_por_campo(url_capa, nombre_campo):
    """
    Cuenta registros agrupando por un campo usando outStatistics.
    Retorna una lista de tuplas (valor, conteo) ordenada de mayor a menor conteo.
    """
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
        "groupByFieldsForStatistics": nombre_campo,
        "f": "json",
    }
    respuesta = consultar_json(url_capa + "/query", parametros)
    conteos = []
    for elemento in respuesta.get("features", []):
        atributos = elemento["attributes"]
        conteos.append((atributos.get(nombre_campo), atributos.get("conteo")))
    conteos.sort(key=lambda par: par[1], reverse=True)
    return conteos


def descargar_muestra(url_capa, cantidad_registros):
    """Descarga los primeros registros de la capa (ordenados por objectid) sin geometría."""
    parametros = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "orderByFields": "objectid",
        "resultOffset": 0,
        "resultRecordCount": cantidad_registros,
        "f": "json",
    }
    respuesta = consultar_json(url_capa + "/query", parametros)
    filas = []
    for elemento in respuesta.get("features", []):
        filas.append(elemento["attributes"])
    return pd.DataFrame(filas)


def calcular_porcentaje_nulos(tabla_muestra):
    """Para cada columna calcula cuántos valores son nulos o cadenas vacías."""
    resultado = []
    total_filas = len(tabla_muestra)
    for nombre_columna in tabla_muestra.columns:
        columna = tabla_muestra[nombre_columna]
        cantidad_nulos = int(columna.isna().sum())
        cantidad_vacios = 0
        if columna.dtype == object:
            texto_columna = columna.dropna().astype(str).str.strip()
            cantidad_vacios = int((texto_columna == "").sum())
        cantidad_total = cantidad_nulos + cantidad_vacios
        porcentaje = 0.0
        if total_filas > 0:
            porcentaje = 100.0 * cantidad_total / total_filas
        resultado.append((nombre_columna, cantidad_nulos, cantidad_vacios, round(porcentaje, 2)))
    return resultado


def describir_formatos(serie_texto):
    """
    Resume los "patrones" de formato de una columna de texto, reemplazando dígitos por 9
    y letras por A. Retorna lista de (patrón, conteo).
    """
    conteo_patrones = {}
    for valor in serie_texto.dropna():
        caracteres_patron = []
        for caracter in str(valor):
            if caracter.isdigit():
                caracteres_patron.append("9")
            elif caracter.isalpha():
                caracteres_patron.append("A")
            else:
                caracteres_patron.append(caracter)
        patron = "".join(caracteres_patron)
        conteo_actual = conteo_patrones.get(patron, 0)
        conteo_patrones[patron] = conteo_actual + 1
    lista_patrones = list(conteo_patrones.items())
    lista_patrones.sort(key=lambda par: par[1], reverse=True)
    return lista_patrones


def contar_coordenadas_fuera_de_medellin(tabla_muestra):
    """Cuenta registros con coordenadas nulas o fuera del rango aproximado de Medellín."""
    latitudes = pd.to_numeric(tabla_muestra["latitud"], errors="coerce")
    longitudes = pd.to_numeric(tabla_muestra["longitud"], errors="coerce")
    sin_coordenadas = latitudes.isna() | longitudes.isna()
    latitud_valida = (latitudes >= LATITUD_MINIMA) & (latitudes <= LATITUD_MAXIMA)
    longitud_valida = (longitudes >= LONGITUD_MINIMA) & (longitudes <= LONGITUD_MAXIMA)
    fuera_de_rango = (~sin_coordenadas) & ~(latitud_valida & longitud_valida)
    ejemplos_fuera = tabla_muestra.loc[fuera_de_rango, ["objectid", "latitud", "longitud", "direccion"]].head(5)
    return int(sin_coordenadas.sum()), int(fuera_de_rango.sum()), ejemplos_fuera


def main():
    load_dotenv()
    url_capa = leer_variable_entorno("URL_ARCGIS_ACCIDENTES", URL_POR_DEFECTO)
    carpeta_datos = asegurar_carpeta_datos_locales()
    secciones = []
    secciones.append("## 1. Siniestros viales — capa ArcGIS `VM_Accidentes`\n")
    secciones.append("Fuente: " + url_capa + "\n")

    # 1. Metadatos
    registro.info("Consultando metadatos de la capa %s", url_capa)
    campos, datos_generales = consultar_metadatos(url_capa)
    for nombre_campo, tipo_campo, _alias in campos:
        registro.info("Campo: %s (%s)", nombre_campo, tipo_campo)
    secciones.append("### Campos y tipos\n")
    secciones.append(
        "Nombre de la capa: **" + str(datos_generales["nombre_capa"]) + "**. "
        "Máximo de registros por consulta: **" + str(datos_generales["maximo_registros_por_consulta"]) + "** "
        "(hay que paginar con `resultOffset` para descargar todo).\n"
    )
    secciones.append(construir_tabla_markdown(["Campo", "Tipo ArcGIS", "Alias"], campos) + "\n")

    # 2. Total de registros
    total_registros = consultar_total_registros(url_capa)
    registro.info("Total de registros en la capa: %d", total_registros)
    secciones.append("### Total de registros\n")
    secciones.append("**" + f"{total_registros:,}" + "** registros.\n")

    # 3. Conteo por año
    conteo_por_anio = contar_por_campo(url_capa, "anio")
    conteo_por_anio.sort(key=lambda par: (par[0] is None, par[0]))
    for anio, conteo in conteo_por_anio:
        registro.info("Año %s: %d registros", anio, conteo)
    secciones.append("### Registros por año\n")
    secciones.append(construir_tabla_markdown(["anio", "Registros"], conteo_por_anio) + "\n")

    # 4. Valores distintos de campos categóricos
    secciones.append("### Valores distintos de campos categóricos\n")
    for nombre_campo in CAMPOS_PARA_VALORES_DISTINTOS:
        conteos = contar_por_campo(url_capa, nombre_campo)
        registro.info("Campo %s: %d valores distintos", nombre_campo, len(conteos))
        for valor, conteo in conteos:
            registro.info("   %s = %s", valor, conteo)
        secciones.append("#### `" + nombre_campo + "` (" + str(len(conteos)) + " valores distintos)\n")
        secciones.append(construir_tabla_markdown(["Valor", "Registros"], conteos) + "\n")

    # 5. Muestra
    registro.info("Descargando muestra de %d registros", TAMANO_MUESTRA)
    tabla_muestra = descargar_muestra(url_capa, TAMANO_MUESTRA)
    ruta_muestra = carpeta_datos / "muestra_siniestros.csv"
    tabla_muestra.to_csv(ruta_muestra, index=False, encoding="utf-8")
    registro.info("Muestra guardada en %s (%d filas)", ruta_muestra, len(tabla_muestra))
    anios_en_muestra = tabla_muestra["anio"].value_counts().sort_index()
    textos_anios = []
    for anio, conteo in anios_en_muestra.items():
        textos_anios.append(str(int(anio)) + " (" + str(conteo) + ")")
    secciones.append("### Muestra descargada\n")
    secciones.append(
        "Se descargaron **" + str(len(tabla_muestra)) + "** registros (ordenados por `objectid`) en "
        "`datos_locales/muestra_siniestros.csv`. Años presentes en la muestra: "
        + ", ".join(textos_anios)
        + ".\n"
    )
    if len(anios_en_muestra) == 1:
        secciones.append(
            "> **Advertencia:** al ordenar por `objectid` la muestra cubre un solo año (fecha mínima "
            + str(tabla_muestra["fecha_siniestro"].min()) + ", máxima " + str(tabla_muestra["fecha_siniestro"].max())
            + "), así que los porcentajes de nulos y formatos no son necesariamente representativos de 2023–2025.\n"
        )

    # 6a. Formato de fecha y hora
    secciones.append("### Formato real de `fecha_siniestro` y `hora_siniestro`\n")
    for nombre_columna in ["fecha_siniestro", "hora_siniestro"]:
        ejemplos = tabla_muestra[nombre_columna].dropna().sample(
            n=min(10, tabla_muestra[nombre_columna].notna().sum()), random_state=7
        )
        lista_ejemplos = []
        for ejemplo in ejemplos:
            lista_ejemplos.append(ejemplo)
        registro.info("Ejemplos de %s: %s", nombre_columna, lista_ejemplos)
        patrones = describir_formatos(tabla_muestra[nombre_columna])
        registro.info("Patrones de %s: %s", nombre_columna, patrones)
        secciones.append("#### `" + nombre_columna + "`\n")
        filas_ejemplos = []
        for ejemplo in lista_ejemplos:
            filas_ejemplos.append(["`" + str(ejemplo) + "`"])
        secciones.append(construir_tabla_markdown(["Ejemplo (10 al azar)"], filas_ejemplos) + "\n")
        secciones.append("Patrones de formato (9 = dígito, A = letra):\n")
        filas_patrones = []
        for patron, conteo in patrones:
            filas_patrones.append(["`" + patron + "`", conteo])
        secciones.append(construir_tabla_markdown(["Patrón", "Registros"], filas_patrones) + "\n")

    # 6b. Nulos por columna
    nulos_por_columna = calcular_porcentaje_nulos(tabla_muestra)
    for nombre_columna, cantidad_nulos, cantidad_vacios, porcentaje in nulos_por_columna:
        registro.info("Columna %s: %d nulos, %d vacíos (%.2f%%)", nombre_columna, cantidad_nulos, cantidad_vacios, porcentaje)
    secciones.append("### Nulos o vacíos por columna (muestra)\n")
    secciones.append(
        construir_tabla_markdown(["Columna", "Nulos", "Vacíos", "% nulo o vacío"], nulos_por_columna) + "\n"
    )

    # 6c. Coordenadas
    cantidad_sin_coordenadas, cantidad_fuera, ejemplos_fuera = contar_coordenadas_fuera_de_medellin(tabla_muestra)
    registro.info("Registros sin coordenadas: %d; fuera del rango de Medellín: %d", cantidad_sin_coordenadas, cantidad_fuera)
    secciones.append("### Coordenadas fuera de Medellín (muestra)\n")
    secciones.append(
        "Rango usado: latitud " + str(LATITUD_MINIMA) + " a " + str(LATITUD_MAXIMA)
        + ", longitud " + str(LONGITUD_MINIMA) + " a " + str(LONGITUD_MAXIMA) + ".\n\n"
        + "- Registros sin latitud o longitud: **" + str(cantidad_sin_coordenadas) + "**\n"
        + "- Registros con coordenadas fuera del rango: **" + str(cantidad_fuera) + "**\n"
    )
    if len(ejemplos_fuera) > 0:
        filas_fuera = ejemplos_fuera.values.tolist()
        secciones.append("\nEjemplos fuera de rango:\n")
        secciones.append(construir_tabla_markdown(["objectid", "latitud", "longitud", "direccion"], filas_fuera) + "\n")

    escribir_seccion_hallazgos("siniestros_arcgis", "\n".join(secciones))
    registro.info("Exploración de siniestros terminada")


if __name__ == "__main__":
    main()
