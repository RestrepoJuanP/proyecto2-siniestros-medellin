# Punto 4 — ETL

## Objetivo

Procesar los datos de `raw/` hacia `trusted/` (limpieza, tipado, unificación de siniestros 2019–2025, normalización de comunas) y de `trusted/` hacia `refined/` (integración de siniestros con clima, población y festivos; agregados para análisis). Salidas en Parquet particionadas por `anio`/`mes`.

- **`glue_jobs/`**: jobs de AWS Glue (rol `LabRole`).
- **`emr/`**: scripts Spark ejecutados como steps en un cluster EMR (terminarlo al finalizar).

## Cómo reproducir

<!-- Pasos exactos, comandos y variables de entorno necesarias. -->

## Evidencias

<!-- Capturas en docs/evidencias/ y enlaces aquí. -->
