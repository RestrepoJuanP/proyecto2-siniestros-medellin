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

## 9. Decisiones del caso (Módulo 1)

Acordadas a partir de la exploración ([punto1_caso_estudio/exploracion/hallazgos.md](punto1_caso_estudio/exploracion/hallazgos.md)). Detalle completo en [punto1_caso_estudio/README.md](punto1_caso_estudio/README.md). **Todos los módulos siguientes deben respetarlas.**

### Corte de fuentes de siniestros

- La capa ArcGIS `VM_Accidentes/0` contiene 2019–2025 (235.820 registros). Se parte así:
  - **RDS MariaDB `movilidad`**: siniestros **2019–2022** (`anio <= 2022`, 157.603 filas), cargados desde la capa para simular el sistema transaccional.
  - **URL (Lambda)**: siniestros **2023–2025** (`where=anio >= 2023`, 78.217 filas), paginando de 2.000 en 2.000 con `resultOffset`.
- Ambas partes tienen las mismas columnas que la capa original y se unen en `trusted/`.

### Llave de comuna y catálogo

- **`codigo_comuna` (int)** es la llave de comuna en todo el proyecto. Se extrae de `num_comuna`: "Comuna 16" → 16, "Corregimiento 90" → 90; `ND`, `SN01`, `SN02` o nulo → NULL.
- La capa de población **no tiene código**, solo `nombre`. El **catálogo de comunas** (en RDS) es el puente: `codigo_comuna`, `nom_comuna`, `nombre_normalizado`.
- `nombre_normalizado` = minúsculas, sin tildes, sin espacios repetidos y sin el prefijo "corregimiento de". Con esta regla cruzan las 21 comunas y corregimientos.
- Los siniestros con `codigo_comuna` NULL (473, 0,2 %) se conservan pero se excluyen de las tasas por comuna.
- El barrio se identifica por la pareja `(barrio, codigo_comuna)`, porque hay nombres de barrio repetidos en varias comunas.

### Deduplicación

- En `trusted/` se deduplica por **`radicado`** (identificador de negocio del siniestro), quedándose con un solo registro por radicado. Esto protege contra traslapes entre RDS y URL y contra reingestas.

### Definiciones operativas

| Concepto | Regla |
|----------|-------|
| Día seco | `precipitation_sum` < 1 mm |
| Lluvia ligera (día) | 1–10 mm |
| Lluvia fuerte (día) | > 10 mm |
| Hora con lluvia | `precipitation` de la hora ≥ 1 mm |
| Franjas horarias | madrugada 00–05, mañana 06–11, tarde 12–17, noche 18–23 |
| Puente | Festivo que cae en lunes + el sábado y el domingo anteriores |
| Tasas | Por cada 10.000 habitantes, con la población proyectada del mismo año |
| Comparación entre tipos de día | Promedio de siniestros por día, nunca totales |

### Columnas derivadas en `trusted/`

`fecha_hora_siniestro`, `codigo_comuna`, `franja_horaria`, `dia_semana`, `es_festivo`, `es_puente`, `precipitacion_dia_mm`, `categoria_lluvia_dia`, `precipitacion_hora_mm` y `hora_con_lluvia` (definidas en el diccionario de datos del README del Punto 1).
