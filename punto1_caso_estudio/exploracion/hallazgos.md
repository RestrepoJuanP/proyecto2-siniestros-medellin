# Hallazgos de la exploración de fuentes (Punto 1)

Archivo generado automáticamente por los scripts de `punto1_caso_estudio/exploracion/`.
Cada sección se reemplaza al volver a ejecutar su script.


<!-- inicio:siniestros_arcgis -->
## 1. Siniestros viales — capa ArcGIS `VM_Accidentes`

Fuente: https://www.medellin.gov.co/servidormapas/rest/services/transporte/VM_Accidentes/MapServer/0

### Campos y tipos

Nombre de la capa: **Siniestralidad**. Máximo de registros por consulta: **2000** (hay que paginar con `resultOffset` para descargar todo).

| Campo | Tipo ArcGIS | Alias |
| --- | --- | --- |
| objectid | esriFieldTypeOID | OBJECTID |
| radicado | esriFieldTypeDouble | radicado |
| fecha_siniestro | esriFieldTypeString | fecha_siniestro |
| hora_siniestro | esriFieldTypeString | hora_siniestro |
| dia | esriFieldTypeString | dia |
| mes | esriFieldTypeString | mes |
| anio | esriFieldTypeDouble | anio |
| clase_siniestro | esriFieldTypeString | clase_siniestro |
| gravedad_siniestro | esriFieldTypeString | gravedad_siniestro |
| direccion | esriFieldTypeString | direccion |
| barrio | esriFieldTypeString | barrio |
| num_comuna | esriFieldTypeString | num_comuna |
| nom_comuna | esriFieldTypeString | nom_comuna |
| latitud | esriFieldTypeDouble | latitud |
| longitud | esriFieldTypeDouble | longitud |
| shape | esriFieldTypeGeometry | Shape |

### Total de registros

**235,820** registros.

### Registros por año

| anio | Registros |
| --- | --- |
| 2019 | 46551 |
| 2020 | 31755 |
| 2021 | 40655 |
| 2022 | 38642 |
| 2023 | 24957 |
| 2024 | 23041 |
| 2025 | 30219 |

### Valores distintos de campos categóricos

#### `gravedad_siniestro` (2 valores distintos)

| Valor | Registros |
| --- | --- |
| HERIDOS | 170751 |
| DAÑOS | 65069 |

#### `clase_siniestro` (6 valores distintos)

| Valor | Registros |
| --- | --- |
| CHOQUE | 134611 |
| OTRO | 50747 |
| ATROPELLO | 26640 |
| VOLCAMIENTO | 11945 |
| CAIDA OCUPANTE | 11846 |
| INCENDIO | 31 |

#### `dia` (7 valores distintos)

| Valor | Registros |
| --- | --- |
| viernes | 35886 |
| martes | 35733 |
| jueves | 35186 |
| lunes | 34587 |
| miércoles | 34512 |
| sábado | 34002 |
| domingo | 25914 |

#### `nom_comuna` (22 valores distintos)

| Valor | Registros |
| --- | --- |
| La Candelaria | 47471 |
| Laureles Estadio | 22594 |
| Castilla | 19799 |
| El Poblado | 16980 |
| Robledo | 16803 |
| Belen | 15950 |
| Aranjuez | 13440 |
| Guayabal | 12998 |
| Buenos Aires | 12443 |
| Villa Hermosa | 8580 |
| Manrique | 8332 |
| La América | 8259 |
| Doce de Octubre | 7911 |
| San Javier | 6032 |
| Santa Cruz | 5606 |
| Popular | 4695 |
| Corregimiento de San Cristobal | 3707 |
| Corregimiento de San Antonio de Prado | 1660 |
| Corregimiento de Altavista | 1117 |
| Corregimiento de Santa Elena | 882 |
| ND | 473 |
| Corregimiento de San Sebastian de Palmitas | 88 |

### Muestra descargada

Se descargaron **2000** registros (ordenados por `objectid`) en `datos_locales/muestra_siniestros.csv`. Años presentes en la muestra: 2019 (2000).

> **Advertencia:** al ordenar por `objectid` la muestra cubre un solo año (fecha mínima 2019-01-01, máxima 2019-01-22), así que los porcentajes de nulos y formatos no son necesariamente representativos de 2023–2025.

### Formato real de `fecha_siniestro` y `hora_siniestro`

#### `fecha_siniestro`

| Ejemplo (10 al azar) |
| --- |
| `2019-01-13` |
| `2019-01-13` |
| `2019-01-03` |
| `2019-01-09` |
| `2019-01-19` |
| `2019-01-04` |
| `2019-01-21` |
| `2019-01-21` |
| `2019-01-21` |
| `2019-01-19` |

Patrones de formato (9 = dígito, A = letra):

| Patrón | Registros |
| --- | --- |
| `9999-99-99` | 2000 |

#### `hora_siniestro`

| Ejemplo (10 al azar) |
| --- |
| `16:20:00` |
| `12:30:00` |
| `16:45:00` |
| `17:25:00` |
| `14:40:00` |
| `13:10:00` |
| `01:10:00` |
| `13:45:00` |
| `08:20:00` |
| `08:50:00` |

Patrones de formato (9 = dígito, A = letra):

| Patrón | Registros |
| --- | --- |
| `99:99:99` | 2000 |

### Nulos o vacíos por columna (muestra)

| Columna | Nulos | Vacíos | % nulo o vacío |
| --- | --- | --- | --- |
| objectid | 0 | 0 | 0 |
| radicado | 0 | 0 | 0 |
| fecha_siniestro | 0 | 0 | 0 |
| hora_siniestro | 0 | 0 | 0 |
| dia | 0 | 0 | 0 |
| mes | 0 | 0 | 0 |
| anio | 0 | 0 | 0 |
| clase_siniestro | 0 | 0 | 0 |
| gravedad_siniestro | 0 | 0 | 0 |
| direccion | 0 | 0 | 0 |
| barrio | 0 | 0 | 0 |
| num_comuna | 0 | 0 | 0 |
| nom_comuna | 0 | 0 | 0 |
| latitud | 0 | 0 | 0 |
| longitud | 0 | 0 | 0 |

### Coordenadas fuera de Medellín (muestra)

Rango usado: latitud 6.1 a 6.4, longitud -75.7 a -75.4.

- Registros sin latitud o longitud: **0**
- Registros con coordenadas fuera del rango: **0**
<!-- fin:siniestros_arcgis -->

<!-- inicio:clima_openmeteo -->
## 2. Clima — API archive de Open-Meteo

Fuente: https://archive-api.open-meteo.com/v1/archive — Medellín (lat 6.2442, lon -75.5812), 2019-01-01 a 2025-12-31, zona horaria `America/Bogota`.

La API ajusta a la celda de su malla: lat **6.2214413**, lon **-75.55185**, elevación **1476.0 m**. Una sola petición devuelve los 7 años (no requiere paginación).

### Cantidad de registros

| Granularidad | Registros | Desde | Hasta |
| --- | --- | --- | --- |
| Horaria | 61368 | 2019-01-01 00:00:00 | 2025-12-31 23:00:00 |
| Diaria | 2557 | 2019-01-01 | 2025-12-31 |

### Nulos por variable

| Variable horaria | Unidad | Nulos | % nulos |
| --- | --- | --- | --- |
| temperature_2m | °C | 0 | 0 |
| precipitation | mm | 0 | 0 |
| rain | mm | 0 | 0 |
| relative_humidity_2m | % | 0 | 0 |

| Variable diaria | Unidad | Nulos | % nulos |
| --- | --- | --- | --- |
| precipitation_sum | mm | 0 | 0 |
| temperature_2m_mean | °C | 0 | 0 |
| temperature_2m_max | °C | 0 | 0 |

### Rango de valores

| Variable horaria | Mínimo | Promedio | Máximo |
| --- | --- | --- | --- |
| temperature_2m | 11.70 | 20.21 | 31.90 |
| precipitation | 0 | 0.25 | 15.80 |
| rain | 0 | 0.25 | 15.80 |
| relative_humidity_2m | 20 | 85.36 | 100 |

| Variable diaria | Mínimo | Promedio | Máximo |
| --- | --- | --- | --- |
| precipitation_sum | 0 | 6.03 | 58.40 |
| temperature_2m_mean | 17.60 | 20.22 | 23.80 |
| temperature_2m_max | 19.60 | 26.18 | 31.90 |

- Horas con precipitación > 0: **22535** de 61368.
- Horas donde `precipitation` ≠ `rain`: **0**.

### Días con precipitación diaria > 10 mm por año

| Año | Días | Días con lluvia (> 0 mm) | Días > 10 mm | Precipitación total (mm) |
| --- | --- | --- | --- | --- |
| 2019 | 365 | 336 | 75 | 1922.80 |
| 2020 | 366 | 344 | 82 | 2197.50 |
| 2021 | 365 | 353 | 86 | 2258 |
| 2022 | 365 | 350 | 115 | 2686.20 |
| 2023 | 365 | 329 | 75 | 1982.80 |
| 2024 | 366 | 336 | 83 | 2176.30 |
| 2025 | 365 | 344 | 92 | 2193.90 |

Archivos generados: `datos_locales/clima_horario.csv`, `datos_locales/clima_diario.csv`.
<!-- fin:clima_openmeteo -->

<!-- inicio:poblacion_comunas -->
## 3. Población por comuna — capa ArcGIS `VC_Distribucion_Poblacional`

Fuente: https://www.medellin.gov.co/servidormapas/rest/services/mapas_nacionales/VC_Distribucion_Poblacional/MapServer/1

### Campos y tipos

Nombre de la capa: **Poblacion - Proyeccion (2018-2030) por comuna y corregimiento**.

| Campo | Tipo ArcGIS | Alias |
| --- | --- | --- |
| objectid | esriFieldTypeOID | OBJECTID |
| nombre | esriFieldTypeString | NOMBRE |
| total_2018 | esriFieldTypeInteger | Total 2018 |
| total_2019 | esriFieldTypeInteger | Total 2019 |
| total_2020 | esriFieldTypeInteger | Total 2020 |
| total_2021 | esriFieldTypeInteger | Total 2021 |
| total_2022 | esriFieldTypeInteger | Total 2022 |
| total_2023 | esriFieldTypeInteger | Total 2023 |
| total_2024 | esriFieldTypeInteger | Total 2024 |
| total_2025 | esriFieldTypeInteger | Total 2025 |
| total_2026 | esriFieldTypeInteger | Total 2026 |
| total_2027 | esriFieldTypeInteger | Total 2027 |
| total_2028 | esriFieldTypeInteger | Total 2028 |
| total_2029 | esriFieldTypeInteger | Total 2029 |
| total_2030 | esriFieldTypeInteger | Total 2030 |
| shape | esriFieldTypeGeometry | Shape |
| fecha_actualizacion | esriFieldTypeDate | fecha_actualizacion |
| st_area(shape) | esriFieldTypeDouble | st_area(shape) |
| st_perimeter(shape) | esriFieldTypeDouble | st_perimeter(shape) |

### Columnas identificadas

- Nombre de comuna/corregimiento: `nombre` (no existe columna de código).
- Población por año: `total_2018`, `total_2019`, `total_2020`, `total_2021`, `total_2022`, `total_2023`, `total_2024`, `total_2025`, `total_2026`, `total_2027`, `total_2028`, `total_2029`, `total_2030` (proyección, formato ancho: una columna por año).
- Registros descargados: **21** en `datos_locales/poblacion_comunas_raw.csv`.
- Población total (suma de filas): 2019 = **2,483,545**, 2025 = **2,745,464**.

| objectid | nombre | total_2019 | total_2022 | total_2025 |
| --- | --- | --- | --- | --- |
| 1 | Popular | 140218 | 147382 | 154823 |
| 2 | Santa Cruz | 115588 | 120959 | 126425 |
| 3 | Manrique | 168724 | 177232 | 185895 |
| 4 | Aranjuez | 142990 | 145325 | 147250 |
| 5 | Castilla | 125276 | 126939 | 128067 |
| 6 | Doce de Octubre | 179493 | 183012 | 186227 |
| 7 | Robledo | 194042 | 204954 | 216194 |
| 8 | Villa Hermosa | 157668 | 168399 | 179508 |
| 9 | Buenos Aires | 160045 | 171416 | 183086 |
| 10 | La Candelaria | 77053 | 78937 | 80444 |
| 11 | Laureles Estadio | 100749 | 101632 | 101487 |
| 12 | La América | 86403 | 87849 | 88714 |
| 13 | San Javier | 161562 | 171854 | 182447 |
| 14 | El Poblado | 108345 | 111343 | 113594 |
| 15 | Guayabal | 65011 | 64856 | 64320 |
| 16 | Belén | 206745 | 214967 | 222266 |
| 17 | San Sebastián de Palmitas | 5689 | 6281 | 6936 |
| 18 | San Cristóbal | 123483 | 144316 | 168924 |
| 19 | Altavista | 40150 | 43556 | 47189 |
| 20 | San Antonio de Prado | 99358 | 112336 | 126953 |
| 21 | Santa Elena | 24953 | 29413 | 34715 |

### Cruce con `num_comuna` / `nom_comuna` de siniestros

Comparación por nombre normalizado (minúsculas, sin tildes, sin el prefijo "Corregimiento de").

| num_comuna (siniestros) | nom_comuna (siniestros) | Siniestros | Código extraído | nombre (población) | Resultado |
| --- | --- | --- | --- | --- | --- |
| Comuna 1 | Popular | 4695 | 1 | Popular | Exacto |
| Comuna 2 | Santa Cruz | 5606 | 2 | Santa Cruz | Exacto |
| Comuna 3 | Manrique | 8332 | 3 | Manrique | Exacto |
| Comuna 4 | Aranjuez | 13440 | 4 | Aranjuez | Exacto |
| Comuna 5 | Castilla | 19799 | 5 | Castilla | Exacto |
| Comuna 6 | Doce de Octubre | 7911 | 6 | Doce de Octubre | Exacto |
| Comuna 7 | Robledo | 16803 | 7 | Robledo | Exacto |
| Comuna 8 | Villa Hermosa | 8580 | 8 | Villa Hermosa | Exacto |
| Comuna 9 | Buenos Aires | 12443 | 9 | Buenos Aires | Exacto |
| Comuna 10 | La Candelaria | 47471 | 10 | La Candelaria | Exacto |
| Comuna 11 | Laureles Estadio | 22594 | 11 | Laureles Estadio | Exacto |
| Comuna 12 | La América | 8259 | 12 | La América | Exacto |
| Comuna 13 | San Javier | 6032 | 13 | San Javier | Exacto |
| Comuna 14 | El Poblado | 16980 | 14 | El Poblado | Exacto |
| Comuna 15 | Guayabal | 12998 | 15 | Guayabal | Exacto |
| Comuna 16 | Belen | 15950 | 16 | Belén | Coincide tras normalizar |
| Corregimiento 50 | Corregimiento de San Sebastian de Palmitas | 88 | 50 | San Sebastián de Palmitas | Coincide tras normalizar |
| Corregimiento 60 | Corregimiento de San Cristobal | 3707 | 60 | San Cristóbal | Coincide tras normalizar |
| Corregimiento 70 | Corregimiento de Altavista | 1117 | 70 | Altavista | Coincide tras normalizar |
| Corregimiento 80 | Corregimiento de San Antonio de Prado | 1660 | 80 | San Antonio de Prado | Coincide tras normalizar |
| Corregimiento 90 | Corregimiento de Santa Elena | 882 | 90 | Santa Elena | Coincide tras normalizar |
| (nulo) | ND | 257 | (nulo) | (nulo) | NO coincide |
| SN01 | ND | 182 | (nulo) | (nulo) | NO coincide |
| SN02 | ND | 34 | (nulo) | (nulo) | NO coincide |

Todos los nombres de la capa de población tienen equivalente en siniestros.

Siniestros cuyo `nom_comuna` no cruza con la población: **473**.
<!-- fin:poblacion_comunas -->
