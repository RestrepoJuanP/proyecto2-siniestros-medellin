# CLAUDE.md — Proyecto 2 Big Data (SI3007, EAFIT)

Guía de contexto y convenciones para cualquier persona (o asistente de IA) que trabaje en este repositorio.

> **Referencia de requisitos:** [docs/enunciado.md](docs/enunciado.md) contiene el enunciado oficial y es la fuente de verdad de lo que exige cada punto.

## 1. Caso de estudio

**"Siniestralidad vial en Medellín y su relación con el clima."**

Se busca integrar datos de siniestros viales de Medellín (2019–2025) con datos meteorológicos horarios, población por comuna y calendario de festivos, para analizar si condiciones como la lluvia, la hora del día o los festivos se relacionan con la cantidad y gravedad de los siniestros.

## 2. Fuentes de datos (3 tipos)

| # | Tipo de fuente | Ubicación | Contenido |
|---|----------------|-----------|-----------|
| a | Base de datos relacional | **RDS MariaDB**, base `movilidad` | Siniestros viales 2019–2022 + catálogo de comunas y barrios |
| b | Archivos en servidor | **EC2**, carpeta `/datos` | CSV de población por comuna y CSV de festivos de Colombia 2019–2025 |
| c | URLs / APIs públicas | Internet | Capa ArcGIS **"VM_Accidentes"** de la Alcaldía de Medellín (siniestros 2023–2025) y **API archive de Open-Meteo** (clima horario de Medellín) |

## 3. Arquitectura del data lake

Un **solo bucket S3** (nombre en la variable `NOMBRE_BUCKET`) con estos prefijos:

| Prefijo | Uso | Formato |
|---------|-----|---------|
| `raw/` | Datos tal cual llegan de la fuente | Original (CSV / JSON) |
| `trusted/` | Datos limpios, tipados y unificados | Parquet |
| `refined/` | Datos integrados / agregados listos para análisis | Parquet |
| `scripts/` | Código de Glue, EMR, bootstrap, etc. | .py / .sh |
| `athena-resultados/` | Resultados de consultas de Athena | — |

Particionamiento:

- `raw/` particionado por **fuente** y **fecha de ingesta**:
  `raw/<fuente>/fecha_ingesta=YYYY-MM-DD/<archivo>`
  Ejemplos de fuente: `rds_siniestros`, `rds_comunas_barrios`, `ec2_poblacion`, `ec2_festivos`, `url_arcgis_accidentes`, `url_openmeteo_clima`.
- `trusted/` y `refined/` en **Parquet**, particionados por `anio=YYYY/mes=MM` cuando la tabla tenga dimensión temporal.

### Bases del Glue Data Catalog

- `siniestros_raw`
- `siniestros_trusted`
- `siniestros_refined`

## 4. Servicios por etapa

| Etapa | Servicios |
|-------|-----------|
| Ingesta desde URL | **Lambda** programada con **EventBridge** (ArcGIS y Open-Meteo → `raw/`) |
| Ingesta de archivos y RDS | **cron en EC2**: copia los CSV de `/datos` y extrae tablas de RDS MariaDB → `raw/` |
| ETL | **AWS Glue** (jobs) y **Spark en EMR** (raw → trusted → refined) |
| Catálogo | **Glue Crawlers** + **Hive en EMR** usando el **Glue Data Catalog como metastore** |
| Consultas | **Athena**, **Hive**, **SparkSQL** |
| API | **API Gateway → Lambda → Athena** |
| Visualización | **Streamlit en EC2** consumiendo la API |

> Streamlit **NO** va detrás de API Gateway porque usa websockets; se expone directamente desde la EC2 (puerto 8501) y consume la API REST.

## 5. Restricciones del AWS Academy Learner Lab

- Región fija: **us-east-1**.
- **No se pueden crear roles IAM.** Usar siempre:
  - `LabRole` para Lambda, Glue, EMR (service role cuando aplique), etc.
  - `LabInstanceProfile` para instancias EC2 y nodos de EMR.
- Las credenciales son **temporales** y cambian en cada sesión del lab: actualizar `~/.aws/credentials` desde "AWS Details" cada vez.
- **Terminar los clusters EMR** al finalizar cada sesión de trabajo (consumen crédito).
- **Nunca subir credenciales** ni el archivo `.env` al repositorio.

## 6. Convenciones de código

- **Python 3.11**.
- Nombres de variables, funciones y columnas **en español y descriptivos** (ej. `fecha_siniestro`, `precipitacion_mm`, `leer_siniestros_rds()`).
- Código **explícito, paso a paso**: sin one-liners comprimidos ni comprensiones anidadas. Preferir bucles claros y variables intermedias con nombre.
- **Comentarios en español.**
- Configuración por **variables de entorno** (`.env`, cargado con `python-dotenv`). **Nunca** credenciales ni nombres de recursos quemados en el código.
- Cada script tiene una función `main()` y usa el módulo `logging` (no `print` para trazas).
- Scripts bash: `set -euo pipefail` y mensajes en español.

Plantilla mínima de script Python:

```python
import logging
import os

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
registro = logging.getLogger(__name__)


def main():
    load_dotenv()
    nombre_bucket = os.environ["NOMBRE_BUCKET"]
    registro.info("Iniciando proceso sobre el bucket %s", nombre_bucket)


if __name__ == "__main__":
    main()
```

## 7. Regla de documentación

**Todo lo que se construya debe quedar documentado en el `README.md` de su carpeta** (objetivo, pasos exactos de "Cómo reproducir" y "Evidencias"), de modo que otra persona pueda reproducirlo desde cero. Las capturas de pantalla van en `docs/evidencias/`.

## 8. Mapa del repositorio

| Carpeta | Contenido |
|---------|-----------|
| `infra/` | Scripts de verificación del entorno y creación/destrucción del data lake |
| `punto1_caso_estudio/` | Definición del caso de estudio |
| `punto2_fuentes/` | Preparación de las fuentes: `rds/`, `ec2/`, `url/` |
| `punto3_ingesta/` | Ingesta automática: `lambda_url/`, `ec2_cron/` |
| `punto4_etl/` | ETL: `glue_jobs/`, `emr/` |
| `punto5_catalogo/` | Crawlers y tablas en Glue Catalog / Hive |
| `punto6_sql/` | Consultas: `athena/`, `hive/`, `sparksql/` |
| `punto7_pyspark/` | Análisis con PySpark |
| `punto8_visualizacion/` | `graficos/`, `api_lambda/`, `streamlit/` |
| `docs/evidencias/` | Capturas y evidencias |
