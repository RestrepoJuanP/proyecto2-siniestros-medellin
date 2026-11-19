# Punto 3 — Ingesta automática

## Objetivo

Automatizar la ingesta de todas las fuentes hacia la zona `raw/` del bucket S3, particionada por fuente y `fecha_ingesta=YYYY-MM-DD`:

- **`lambda_url/`**: funciones Lambda (rol `LabRole`) programadas con EventBridge que descargan ArcGIS y Open-Meteo.
- **`ec2_cron/`**: scripts ejecutados por cron en EC2 (`LabInstanceProfile`) que suben los CSV de `/datos` y extraen las tablas de RDS MariaDB.

## Cómo reproducir

<!-- Pasos exactos, comandos y variables de entorno necesarias. -->

## Evidencias

<!-- Capturas en docs/evidencias/ y enlaces aquí. -->
