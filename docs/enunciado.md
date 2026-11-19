# Enunciado oficial — Proyecto 2 (SI3007, EAFIT)

Este archivo es la referencia de requisitos de cada punto del proyecto.

## Requisitos

1. Crear un caso de estudio donde procese datos almacenados en fuentes de datos Bases de Datos, Archivos y URL. Conseguir un conjunto de datos (típicamente datasets públicos), almacenar una parte en bases de datos como fuente, y plantear al menos 5 preguntas/hipótesis de negocio que se contestarán con estos datos.
2. Fuentes de datos: simular datos en RDS MariaDB, archivos en una instancia de EC2 y URLs en Internet.
3. Ingesta de datos hacia el Datalake (AWS S3) en las zonas correctas. Debe ser un proceso automático.
4. Procesamiento orientado a la preparación de datos (zona raw a trusted, o en medallion bronze a silver). Herramientas: AWS Glue y Apache Spark.
5. Catalogación de tablas SQL con herramientas como AWS Glue y EMR/Hive.
6. Consultas y procesamiento analítico descriptivo con SQL usando AWS Athena, EMR/Hive y SparkSQL.
7. Consultas y procesamiento analítico descriptivo con Spark en Python (pyspark).
8. Aplicación de visualización de datos (matplotlib, dash, PowerBI, grafana, etc.) y alguna aplicación expuesta mediante API Gateway con Streamlit de Python.

## Entrega

Un documento con evidencias de cada punto (descripciones, pantallazos, extractos de código) y un repositorio GitHub con un directorio por cada punto, con evidencias, código fuente e instrucciones y archivos para que otra persona pueda reproducir todo el proyecto.
