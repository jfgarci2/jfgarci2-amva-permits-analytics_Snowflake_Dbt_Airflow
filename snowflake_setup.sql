-- =====================================================================
-- snowflake_setup.sql  —  AMVA_ENV + usuario de servicio AMVA_DBT
-- Correr COMPLETO en Snowsight: flecha junto a ▶  →  "Run all"
-- (o Ctrl+Shift+Enter). Si solo das ▶, corre UNA línea (la del cursor).
-- ANTES de correr: cambia CAMBIA_ESTA_CLAVE por tu contraseña.
-- =====================================================================

USE ROLE ACCOUNTADMIN;

-- 1) Base de datos y capas (propiedad de SYSADMIN, que es el rol de dbt)
USE ROLE SYSADMIN;
CREATE DATABASE IF NOT EXISTS AMVA_ENV;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;

-- 2) El warehouse lo creó ACCOUNTADMIN: SYSADMIN necesita permiso para usarlo
USE ROLE ACCOUNTADMIN;
GRANT USAGE, OPERATE ON WAREHOUSE AMVA_WH TO ROLE SYSADMIN;

-- 3) Usuario de servicio para dbt (password nativa, sin MFA)
USE ROLE ACCOUNTADMIN;
CREATE USER IF NOT EXISTS AMVA_DBT
  PASSWORD             = 'CAMBIA_ESTA_CLAVE'
  TYPE                 = LEGACY_SERVICE
  DEFAULT_ROLE         = SYSADMIN
  DEFAULT_WAREHOUSE    = AMVA_WH
  DEFAULT_NAMESPACE    = AMVA_ENV.SILVER
  MUST_CHANGE_PASSWORD = FALSE;

-- Si el usuario ya existía, esto le fija la clave de nuevo:
ALTER USER AMVA_DBT SET PASSWORD = 'CAMBIA_ESTA_CLAVE' MUST_CHANGE_PASSWORD = FALSE;

GRANT ROLE SYSADMIN TO USER AMVA_DBT;

-- 4) Verificación (deben salir filas)
SHOW DATABASES LIKE 'AMVA_ENV';
SHOW SCHEMAS IN DATABASE AMVA_ENV;
SHOW USERS LIKE 'AMVA_DBT';
SHOW GRANTS TO USER AMVA_DBT;
