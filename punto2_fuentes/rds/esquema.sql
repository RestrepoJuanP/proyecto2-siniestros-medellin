-- -----------------------------------------------------------------------------
-- esquema.sql
-- Esquema de la base "movilidad" en RDS MariaDB (fuente relacional del proyecto).
-- Idempotente: usa CREATE TABLE IF NOT EXISTS. Se aplica con cargar_rds.py
-- conectado a la base indicada en RDS_BASE (no se fija la base aquí).
-- Orden: comunas -> barrios -> siniestros (por las llaves foráneas).
-- -----------------------------------------------------------------------------

-- Catálogo de comunas y corregimientos (puente con la población por nombre_normalizado)
CREATE TABLE IF NOT EXISTS comunas (
    codigo_comuna      INT          NOT NULL COMMENT 'Número extraído de num_comuna: Comuna 16 -> 16, Corregimiento 90 -> 90',
    nombre_comuna      VARCHAR(100) NOT NULL COMMENT 'nom_comuna tal como viene en la capa de siniestros',
    nombre_normalizado VARCHAR(100) NOT NULL COMMENT 'Mayúsculas, sin tildes y sin el prefijo Corregimiento de',
    tipo               ENUM('COMUNA', 'CORREGIMIENTO') NOT NULL,
    PRIMARY KEY (codigo_comuna),
    UNIQUE KEY uk_comunas_nombre_normalizado (nombre_normalizado)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Catálogo de barrios. Un mismo nombre puede existir en varias comunas.
-- nombre_barrio usa collation binaria para conservar el texto exacto de la fuente
-- (con unicode_ci, "Belén" y "Belen" chocarían en el índice único).
CREATE TABLE IF NOT EXISTS barrios (
    id_barrio     INT          NOT NULL AUTO_INCREMENT,
    nombre_barrio VARCHAR(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    codigo_comuna INT          NULL COMMENT 'NULL cuando la comuna es ND / SN01 / SN02 / vacía',
    PRIMARY KEY (id_barrio),
    UNIQUE KEY uk_barrios_nombre_comuna (nombre_barrio, codigo_comuna),
    CONSTRAINT fk_barrios_comunas FOREIGN KEY (codigo_comuna) REFERENCES comunas (codigo_comuna)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Siniestros viales 2019-2022 (simula el sistema transaccional de movilidad)
CREATE TABLE IF NOT EXISTS siniestros (
    objectid            INT           NOT NULL COMMENT 'Identificador de la capa ArcGIS VM_Accidentes',
    radicado            BIGINT        NULL     COMMENT 'Identificador de negocio; llave de deduplicación en trusted',
    fecha_siniestro     DATE          NULL,
    hora_siniestro      TIME          NULL,
    dia                 VARCHAR(20)   NULL,
    mes                 VARCHAR(20)   NULL,
    anio                SMALLINT      NULL,
    clase_siniestro     VARCHAR(50)   NULL,
    gravedad_siniestro  VARCHAR(20)   NULL,
    direccion           VARCHAR(255)  NULL,
    barrio              VARCHAR(150)  NULL,
    num_comuna          VARCHAR(50)   NULL,
    nom_comuna          VARCHAR(100)  NULL,
    codigo_comuna       INT           NULL     COMMENT 'Derivado de num_comuna; NULL si ND / SN01 / SN02 / vacío',
    latitud             DECIMAL(10,7) NULL,
    longitud            DECIMAL(10,7) NULL,
    fecha_actualizacion TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                                      COMMENT 'Se actualiza solo si cambia algún valor de la fila',
    PRIMARY KEY (objectid),
    KEY idx_siniestros_radicado (radicado),
    KEY idx_siniestros_fecha_siniestro (fecha_siniestro),
    KEY idx_siniestros_codigo_comuna (codigo_comuna),
    KEY idx_siniestros_fecha_actualizacion (fecha_actualizacion),
    CONSTRAINT fk_siniestros_comunas FOREIGN KEY (codigo_comuna) REFERENCES comunas (codigo_comuna)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
