-- -----------------------------------------------------------------------------
-- consultas_verificacion.sql
-- Consultas de evidencia sobre la base "movilidad" en RDS MariaDB.
-- Ejecutar conectado a la base (cliente mysql/mariadb, DBeaver o MySQL Workbench).
-- -----------------------------------------------------------------------------

-- 1. Conteo de siniestros por año (esperado según Módulo 1:
--    2019 = 46.551, 2020 = 31.755, 2021 = 40.655, 2022 = 38.642; total 157.603)
SELECT anio,
       COUNT(*) AS total_siniestros
FROM siniestros
GROUP BY anio
ORDER BY anio;

-- 2. Top 10 comunas con más siniestros 2019-2022
SELECT codigo_comuna,
       nom_comuna,
       COUNT(*) AS total_siniestros
FROM siniestros
GROUP BY codigo_comuna, nom_comuna
ORDER BY total_siniestros DESC
LIMIT 10;

-- 3. Conteo por gravedad y su porcentaje
SELECT gravedad_siniestro,
       COUNT(*) AS total_siniestros,
       ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM siniestros), 2) AS porcentaje
FROM siniestros
GROUP BY gravedad_siniestro
ORDER BY total_siniestros DESC;

-- 4. Join siniestros - comunas: siniestros con heridos por comuna y tipo,
--    incluyendo los que no tienen comuna (LEFT JOIN -> nombre NULL)
SELECT c.tipo,
       c.codigo_comuna,
       c.nombre_normalizado,
       COUNT(*) AS total_siniestros,
       SUM(CASE WHEN s.gravedad_siniestro = 'HERIDOS' THEN 1 ELSE 0 END) AS siniestros_con_heridos
FROM siniestros AS s
LEFT JOIN comunas AS c
       ON s.codigo_comuna = c.codigo_comuna
GROUP BY c.tipo, c.codigo_comuna, c.nombre_normalizado
ORDER BY c.tipo, c.codigo_comuna;

-- 5. Muestra de 10 filas
SELECT objectid,
       radicado,
       fecha_siniestro,
       hora_siniestro,
       dia,
       clase_siniestro,
       gravedad_siniestro,
       barrio,
       num_comuna,
       codigo_comuna,
       latitud,
       longitud,
       fecha_actualizacion
FROM siniestros
ORDER BY objectid
LIMIT 10;
