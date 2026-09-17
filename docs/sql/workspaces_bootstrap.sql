-- =============================================================================
-- AMVA — bootstrap Snowflake (Workspaces de Snowsight)
-- =============================================================================
-- NO pegues este archivo entero y des Run una sola vez.
-- Workspaces COMPILA todo el SQL a la vez. Si AMVA_ENV aún no existe,
-- CREATE SCHEMA AMVA_ENV.BRONZE falla: "database does not exist".
-- El botón Run a veces ejecuta SOLO la última sentencia.
--
-- Copia CADA bloque (RUN 1, RUN 2, ...) a Untitled.sql, borra el resto, Run.
-- Rol UI: ACCOUNTADMIN. Warehouse UI: AMVA_WH.
-- =============================================================================

-- RUN 1 — solo la database (warehouse AMVA_WH ya existe en Compute)
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS AMVA_ENV;

-- RUN 2 — esquemas (la base YA tiene que existir)
USE ROLE ACCOUNTADMIN;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;

-- RUN 3 — usuario nativo para dbt (NO es Gmail, NO es jfgarci206)
-- Cambia la password si rotas la clave; la misma va en profiles.yml (gitignored).
USE ROLE ACCOUNTADMIN;
CREATE USER AMVA_DBT PASSWORD = 'AmvaDbt2026' MUST_CHANGE_PASSWORD = FALSE;

-- RUN 4 — rol que pide profiles.yml
USE ROLE ACCOUNTADMIN;
GRANT ROLE SYSADMIN TO USER AMVA_DBT;

-- RUN 5 — permisos sobre objetos que YA existen
USE ROLE ACCOUNTADMIN;
GRANT USAGE ON WAREHOUSE AMVA_WH TO ROLE SYSADMIN;
GRANT USAGE ON DATABASE AMVA_ENV TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.BRONZE TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.SILVER TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.GOLD TO ROLE SYSADMIN;

-- =============================================================================
-- RUN 6 y RUN 7 — comprobar horas hábiles (DESPUÉS de dbt run)
-- Una sola sentencia por Run. Warehouse UI: AMVA_WH.
-- No pegues RUN 6 y RUN 7 juntos.
-- =============================================================================

-- RUN 6 — conteo y promedio (una sentencia)
SELECT
    COUNT(*) AS filas,
    COUNT(horas_habiles) AS con_horas,
    ROUND(AVG(horas_habiles), 2) AS avg_horas_habiles
FROM AMVA_ENV.SILVER.INT_HORAS_HABILES;

-- RUN 7 — cinco tareas con horas > 0 (una sentencia)
SELECT
    tramite_id,
    tarea_orden,
    tarea_nombre,
    fecha_inicia_tarea,
    fecha_finaliza_tarea,
    horas_habiles,
    dias_habiles
FROM AMVA_ENV.SILVER.INT_HORAS_HABILES
WHERE horas_habiles > 0
LIMIT 5;

-- =============================================================================
-- RUN 8 — comprobar mart de trámite (DESPUÉS de dbt run mart_tramites_geo)
-- Una sola sentencia. Warehouse UI: AMVA_WH. No lo pegues junto con RUN 6/7.
-- Esperado (15 sep 2026): TRAMITES=4025, CON_COORDENADAS=1182,
-- MUNICIPIOS=19, AVG_DIAS_HABILES_SGC≈111.02
-- =============================================================================

-- RUN 8 — grano trámite + cobertura GPS real (una sentencia)
SELECT
    COUNT(*) AS tramites,
    COUNT(latitud) AS con_coordenadas,
    COUNT(DISTINCT municipio) AS municipios,
    ROUND(AVG(dias_habiles_sgc), 2) AS avg_dias_habiles_sgc
FROM AMVA_ENV.GOLD.MART_TRAMITES_GEO;

