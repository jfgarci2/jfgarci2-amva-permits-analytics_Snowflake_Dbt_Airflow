# Informe técnico — AMVA permisos ambientales

**Proyecto:** Analytics Engineering end-to-end (dbt + Snowflake trial + Airflow + tablero HTML)  
**Autor:** José Fernando García (ingeniero civil, GIS, Data Analyst)  
**Contexto:** portafolio para entrevista Factored (Data Analytics), entrevistadora Fátima  
**Fecha de este corte:** 15 de septiembre de 2026  
**Cuenta Snowsight (sin contraseña):** display `JOSE GARCIA`, login name `jfgarci206` (`CURRENT_USER`), rol UI `ACCOUNTADMIN`, URL `https://app.snowflake.com/nvsmazv/be58602/`  
**Account identifier (SELECT, SUCCESS):** `NVSMAZV-BE58602`  
**dbt (SUCCESS 15 sep 2026):** `Connection test: [OK]` / `All checks passed!` User **`AMVA_DBT`**, role **SYSADMIN**, warehouse **`AMVA_WH`**, database **`AMVA_ENV`**, schema **SILVER**, account **`NVSMAZV-BE58602`**. [`profiles.yml`](../profiles.yml) en la raíz (gitignored). Snowsight = Google; dbt = usuario nativo `AMVA_DBT` (no Gmail, no SAML). Receta real: [sección 12](#12-cómo-se-conecta-dbt-de-verdad-lo-que-funcionó-y-por-qué-demoró).  
**Calendario de tiempo:** todo `DiasHabiles` / `HorasTotales` (jornada 7:30–17:30, sin sábados/domingos/festivos) usa `Bases de datos AMVA/raw/DIAS_NOLABORABLES.xlsx`.  
**Archivo de clase corta:** [`manual/MANUAL_CLASE_A_CLASE.md`](../manual/MANUAL_CLASE_A_CLASE.md)

Este informe **lleva el SQL / YAML que ya existe** (warehouse + medallón + `profiles.yml` + staging + horas hábiles + mart trámite + tablero HTML). Los modelos de negocio vivos están en la [sección 6](#6-sql-dbt-horas-hábiles-y-mart-sgc). Cómo abrir el visor: [sección 13](#13-tablero-html-leaflet). Airflow y CI **aún no**.

**Regla de oro:** no pegar contraseñas, tokens ni `.env` en GitHub ni en este archivo.

---

## Índice

1. [Qué es el proyecto y el stack](#1-qué-es-el-proyecto-y-el-stack)
2. [Trial: por qué no se paga (créditos = warehouse encendido)](#2-trial-por-qué-no-se-paga-créditos--warehouse-encendido)
3. [SQL del warehouse `AMVA_WH`](#3-sql-del-warehouse-amva_wh)
4. [SQL de database y schemas medallón](#4-sql-de-database-y-schemas-medallón-bronze-silver-gold)
5. [Cómo leer el account identifier](#5-cómo-leer-el-account-identifier)
6. [SQL dbt: horas hábiles y mart SGC](#6-sql-dbt-horas-hábiles-y-mart-sgc)
7. [Doble destino: Snowflake trial y DuckDB](#7-doble-destino-snowflake-trial-y-duckdb)
8. [Frases B2 cortas para la entrevista](#8-frases-b2-cortas-para-la-entrevista)
9. [Capturas Snowsight](#9-capturas-snowsight)
10. [profiles.yml en esta carpeta (gitignored)](#10-profilesyml-en-esta-carpeta-gitignored)
11. [Calendario DIAS_NOLABORABLES (motor de DiasHabiles)](#11-calendario-dias_nolaborables-motor-de-diashabiles)
12. [Cómo se conecta dbt de verdad (lo que funcionó y por qué demoró)](#12-cómo-se-conecta-dbt-de-verdad-lo-que-funcionó-y-por-qué-demoró)
13. [Tablero HTML (Leaflet)](#13-tablero-html-leaflet)

---

## 1. Qué es el proyecto y el stack

Construimos un pipeline **pequeño, barato y explicable** sobre permisos ambientales del AMVA (extractos del sistema operativo **DECIDE**). No nos conectamos a Oracle. El AMVA entrega un Excel/CSV cada cierto tiempo. Nosotros lo anonimizamos (Ley 1581), lo modelamos con dbt y publicamos un tablero HTML estático.

```
DECIDE (Oracle, operación AMVA)     →  yo NO me conecto aquí
        ↓
        Excel/CSV periódico
        ↓
data/raw/  (git-ignored; puede tener PII)
        ↓
        Python: quitar PII (CODFUNCIONARIO, FUNCIONARIO, TERCERO)
        ↓
data/anon/  →  Snowflake BRONZE (tabla cruda)
        ↓
        dbt Core
        ↓
Snowflake SILVER (staging) → GOLD (marts)
        ↓
        script export
        ↓
dashboard/data/*.json
        ↓
dashboard/index.html  (Leaflet + JS; GitHub Pages / Vercel)
```

**Analogía GIS:** DECIDE es la geodatabase corporativa. El Excel es el shapefile exportado que te pasan. Python es el paso de “quitar campos sensibles”. Snowflake es la GDB de analítica. dbt es ModelBuilder. El JSON es un GeoJSON derivado. El HTML es el visor. Airflow (al final, no el día 1) es el scheduler que corre el toolbox cuando cae un shape nuevo.

| Capa | Quién | Qué hace |
|------|--------|----------|
| Disco + cómputo SQL | Snowflake trial, warehouse **XS** | Guarda tablas y ejecuta SQL. Cobra **mientras el warehouse está encendido**. |
| Transformación | dbt Core 1.9+ / `dbt-snowflake` | Compila SQL (`ref`, `source`, tests) y lo manda a Snowflake. |
| Ingesta / PII | Python | Anonimiza antes de cargar Bronze. |
| Orquestación | Airflow **al final**, local | Agenda: archivo nuevo → anonimizar → Bronze → `dbt build` → export JSON. |
| Tablero | HTML + JS + Leaflet | Dibuja KPIs y mapa. **No** consulta Snowflake desde el navegador. |
| CI ligero | GitHub Actions (si hay tiempo) | Corre tests después de `dbt build`. Nunca Azure Data Factory en este repo. |

**Frase B2:** "Snowflake stores and computes. dbt transforms. Airflow schedules. The HTML dashboard only draws JSON."

### Lo que ya está hecho (15 sep 2026)

- Cuenta trial creada. Display `JOSE GARCIA`. Login name **`jfgarci206`** (`CURRENT_USER`). Rol en UI: `ACCOUNTADMIN`.
- Crédito de prueba **$400 of $400 remaining**, **30 days**. No pulsar **Upgrade**.
- Warehouse de proyecto **`AMVA_WH`** creado en la UI (Standard **Gen1**, X-Small, auto-suspend **1 min**, auto-resume, sin multi-cluster, sin query acceleration).
- Tras crearlo quedó **Started**; se reanudó ~15 s; luego se **suspendió**. Los **3** warehouses de la cuenta están **Suspended** salvo cuando un SQL reanuda `AMVA_WH`.
- **No existe `COMPUTE_WH`** en este trial. Hay `SNOWFLAKE_LEARNING_WH` y `SYSTEM$STREAMLIT_NOTEBOOK_WH`. **No usarlos** para dbt ni para este proyecto.
- Snowsight **Workspaces** (`Projects` → `Workspaces`): se abrió un **SQL file** (`Untitled.sql`). **No** es un Snowflake dbt Project; dbt irá en local más adelante.
- DDL de **`AMVA_ENV`** + schemas **BRONZE / SILVER / GOLD** corrido con éxito. Warehouse del picker: **`AMVA_WH` (X-Small)**. El dropdown de rol sigue en **ACCOUNTADMIN**; el SQL tenía `USE ROLE SYSADMIN`.
- `SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME()` devolvió **`NVSMAZV-BE58602`** (SUCCESS, 1 row). Captura: [`11-account-identifier-nvsmazv-be58602.png`](screenshots/11-account-identifier-nvsmazv-be58602.png).
- `SELECT CURRENT_USER() AS usuario, CURRENT_ROLE() AS rol` devolvió **`jfgarci206` / `ACCOUNTADMIN`** (SUCCESS, 1 row, 56 ms). Captura: [`12-current-user-jfgarci206.png`](screenshots/12-current-user-jfgarci206.png). El dropdown de rol sigue en ACCOUNTADMIN; si solo se corre el último `SELECT`, el `USE ROLE SYSADMIN` de arriba **no** cambia `CURRENT_ROLE`.
- `profiles.yml` de trabajo **en la raíz de este proyecto** (misma carpeta que `PROMPT` / `amva_pipeline`). Git lo ignora. Perfil `amva_pipeline`, target `snowflake`, rol **SYSADMIN**, schema **SILVER**, password = `env_var('SNOWFLAKE_PASSWORD')`. Segundo target: **DuckDB** → `data/processed/amva.duckdb`. Staging Silver ya corre (`stg_permisos`, `stg_dias_nolaborables`). Horas hábiles: `SILVER.INT_HORAS_HABILES` + mart delgado `GOLD.MART_TAREAS_SGC` (Snowsight RUN 6: 216414 filas, 214483 con horas, avg 49.59 h; RUN 7: trámite 1391640). Mart trámite: `GOLD.MART_TRAMITES_GEO` + JSON [`dashboard/data/mart_tramites.json`](../dashboard/data/mart_tramites.json) + visor [`dashboard/index.html`](../dashboard/index.html) (RUN 8: 4025 trámites, 1182 GPS, 19 municipios, 111.02 días hábiles). Extractos AMVA en [`Bases de datos AMVA/raw/`](../Bases%20de%20datos%20AMVA/raw/) (xlsx gitignored). Trial **$400 of $400**.

**Verdad para la entrevista:** este repo es **desde cero**. No inventes Snowflake, Airflow ni Azure Data Factory en producción. El otro proyecto (catastro Medellín + Databricks) y el AMVA + DuckDB son **otros repos**; de ahí solo reutilizamos la *idea* y los archivos de datos cuando los copies.

**Frase B2:** "This is a trial project from scratch. I practiced Snowflake and dbt here. I did not run ADF in production."

---

## 2. Trial: por qué no se paga (créditos = warehouse encendido)

Snowflake separa **almacenamiento** y **cómputo**.

- **Almacenamiento** = las tablas (como la geodatabase en disco). En un trial pequeño casi no pesa.
- **Cómputo** = el **virtual warehouse**. Es el motor que corre SELECT, COPY, `dbt build`. **Solo cobra mientras está Started / Running.**

Un X-Small Gen1 consume **1 crédito/hora** mientras está encendido (visto en el diálogo de creación). `AUTO_SUSPEND = 60` apaga el motor a los **60 segundos** de inactividad. `AUTO_RESUME = TRUE` lo enciende solo cuando llega un SQL que lo necesita.

Por eso el trial de **$400 / 30 días no se “gasta solo”**: se gasta si dejas el warehouse **Started**. Captura de home: [`01-snowsight-home-trial-400.png`](screenshots/01-snowsight-home-trial-400.png). Lista con los tres warehouses apagados: [`07-amva-wh-suspended.png`](screenshots/07-amva-wh-suspended.png).

**No pulsar Upgrade.** Eso pasa la cuenta a pago.

**Analogía GIS:** el shapefile en el disco no consume electricidad. ArcGIS / el geoproceso sí. Suspender el warehouse es apagar el PC de geoproceso y dejar la GDB guardada.

**Frase B2:** "Credits are billed while the warehouse is running, not for stored data."

### Warehouses que ya había en el trial

Captura: [`02-warehouses-learning-wh-suspended.png`](screenshots/02-warehouses-learning-wh-suspended.png).

| Warehouse | ¿Usarlo? | Nota |
|-----------|----------|------|
| `COMPUTE_WH` | No existe | Tutoriales viejos lo mencionan. **Esta trial no lo tiene.** |
| `SNOWFLAKE_LEARNING_WH` | No | Warehouse de aprendizaje de Snowflake (XS). No es el del proyecto. |
| `SYSTEM$STREAMLIT_NOTEBOOK_WH` | **No** | Warehouse interno de Streamlit/Notebooks. No lo uses para dbt. |
| `AMVA_WH` | **Sí** | El único warehouse del proyecto. |

**Frase B2:** "This trial has no COMPUTE_WH. I created AMVA_WH as X-Small Gen1."

### Roles: ACCOUNTADMIN vs SYSADMIN

En la UI estás como **ACCOUNTADMIN** (administrador total de la cuenta). Sirve para el alta. Para el trabajo diario usa **SYSADMIN** (crear warehouses, bases y schemas). Así no mezclas “root” con analítica.

**Frase B2:** "I use SYSADMIN for daily work, not ACCOUNTADMIN."

El warehouse se creó en la UI con `ACCOUNTADMIN` como owner. El SQL de este informe usa `SYSADMIN` (buena práctica). Si un `CREATE` o un `GRANT` falla por permisos, vuelve un momento a `ACCOUNTADMIN`, otorga el permiso y regresa a `SYSADMIN`. El bloque de `GRANT` está al final de la [sección 3](#si-el-warehouse-ya-existe-creado-en-la-ui).

---

## 3. SQL del warehouse `AMVA_WH`

### Lo que ya hiciste en la UI (evidencia)

1. **Diálogo por defecto** ([`03-new-warehouse-dialog.png`](screenshots/03-new-warehouse-dialog.png)): Type **Standard (Gen2)**, Size X-Small, Auto-resume, Auto-suspend **5 min**. Gen2 sale más caro; no lo dejamos así.
2. **Valores reales al crear** ([`04-new-warehouse-amva-wh-settings.png`](screenshots/04-new-warehouse-amva-wh-settings.png)):
   - Name: `AMVA_WH`
   - Type: **Standard (Gen1)**
   - Size: **X-Small**
   - Auto-resume: sí
   - Auto-suspend: **1 min** (60 segundos)
   - Multi-cluster: **no**
   - Query acceleration: **no**
   - Costo mostrado: **1 credit/hour**
3. Tras Create quedó **Started** 1/1 clusters ([`05-amva-wh-created-started.png`](screenshots/05-amva-wh-created-started.png)).
4. Más tarde apareció **Resumed 15 seconds ago**, resource constraint **`STANDARD_GEN_1`** ([`06-amva-wh-resumed-15s.png`](screenshots/06-amva-wh-resumed-15s.png)).
5. Estado final de esta clase: los **3** warehouses **Suspended** ([`07-amva-wh-suspended.png`](screenshots/07-amva-wh-suspended.png)).

El SQL de abajo **reproduce esa configuración**. Si el warehouse ya existe, `CREATE IF NOT EXISTS` no lo pisa: usa el `ALTER`.

Corre esto en un **SQL file** de Snowsight **Workspaces** (no Worksheet clásico; no dbt Project de Snowflake). Si pide warehouse, elige `AMVA_WH`. Luego **vuelve a suspender**.

---

### 3.1 Elegir el rol de trabajo

```sql
USE ROLE SYSADMIN;
```

**Qué hace:** cambia el rol de la sesión a `SYSADMIN`.  
**Por qué:** crear cómputo y bases es trabajo de SYSADMIN, no de ACCOUNTADMIN.  
**Analogía GIS:** no editas la geodatabase corporativa con la cuenta de administrador de dominio; usas el rol de GIS admin.

---

### 3.2 Crear el warehouse (equivalente a la UI)

`GENERATION = '1'` **sí es válido** en el SQL actual de Snowflake (`CREATE WAREHOUSE`: valores `'1'` o `'2'`, **con comillas**). Equivale a `RESOURCE_CONSTRAINT = STANDARD_GEN_1`. Lo incluimos porque:

- en la UI elegiste **Gen1** (Gen2 cuesta más);
- si omites `GENERATION`, Snowflake puede crear **Gen2 por defecto** en regiones donde ya está disponible.

```sql
USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS AMVA_WH
  WAREHOUSE_SIZE = 'XSMALL'
  WAREHOUSE_TYPE = STANDARD
  GENERATION = '1'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 300
  COMMENT = 'AMVA dbt - XS, auto-suspend 60s';
```

**Qué hace:** crea un motor virtual llamado `AMVA_WH` si aún no existe. No crea tablas.  
**Por qué cada parámetro:**

| Parámetro | Valor | Significado |
|-----------|--------|-------------|
| `WAREHOUSE_SIZE` | `XSMALL` | El más barato. 1 crédito/hora Gen1. Suficiente para ~200 mil filas. |
| `WAREHOUSE_TYPE` | `STANDARD` | Warehouse clásico de SQL analítico. No Snowpark-Optimized. No Adaptive. |
| `GENERATION` | `'1'` | Hardware Gen1, como en la UI. **Las comillas son obligatorias** (`'1'`, no `1`). |
| `AUTO_SUSPEND` | `60` | Se apaga a los 60 s sin consultas. En la UI era “1 min”. |
| `AUTO_RESUME` | `TRUE` | Si llega un SQL y está Suspended, Snowflake lo enciende solo. |
| `INITIALLY_SUSPENDED` | `TRUE` | Nace apagado. En la UI nació **Started** y hubo que suspenderlo a mano. |
| `STATEMENT_TIMEOUT_IN_SECONDS` | `300` | Mata una consulta a los 5 minutos. Evita un `dbt` colgado que deje el XS encendido. |
| `COMMENT` | texto | Etiqueta humana. No afecta el cobro. |

No hay `MAX_CLUSTER_COUNT` extra: queda **1 cluster** (sin multi-cluster). No hay `ENABLE_QUERY_ACCELERATION`: queda apagado.

**Analogía GIS:** esto no es “crear la GDB”. Es **comprar un PC X-Small de geoproceso**, configurarlo para que se apague al minuto y no arranque hasta que corras un modelo.

**Frase B2:** "I created an X-Small Gen1 warehouse with auto-suspend of 60 seconds to keep the trial cheap."

---

### 3.3 Alinear el warehouse si ya existe (tu caso)

`CREATE IF NOT EXISTS` **no cambia** un warehouse que ya creaste en la UI. Este `ALTER` deja tamaño, suspend, resume y timeout iguales al estándar del proyecto.

```sql
ALTER WAREHOUSE AMVA_WH SET
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 300;
```

**Qué hace:** actualiza propiedades del warehouse existente. No borra datos (el warehouse no guarda tablas).  
**Por qué:** tu `AMVA_WH` ya existe. Esto es el “match” SQL de la UI.  
**Analogía GIS:** cambias las opciones del geoproceso (timeout, apagado automático), no el contenido de las capas.

Si quisieras **forzar Gen1** por SQL (la UI ya lo dejó en `STANDARD_GEN_1`):

```sql
ALTER WAREHOUSE AMVA_WH SET GENERATION = '1';
```

**Qué hace:** fija generación 1.  
**Por qué:** documentar el equivalente SQL; en tu cuenta ya es Gen1.  
**Analogía GIS:** eliges la versión del motor de geoproceso, no una herramienta más cara.

---

### 3.4 Suspender (apagar el cobro)

```sql
ALTER WAREHOUSE AMVA_WH SUSPEND;
```

**Qué hace:** apaga el cómputo ahora. Estado: **Suspended**.  
**Por qué:** tras Create la UI lo dejó **Started**. Cada segundo encendido gasta trial. El auto-suspend de 60 s también lo apaga, pero no esperamos.  
**Analogía GIS:** cierras ArcGIS al terminar; no dejas el geoproceso corriendo “por si acaso”.

**Frase B2:** "After I finish, I suspend the warehouse so the trial does not burn credits."

`USE WAREHOUSE AMVA_WH` o un `SELECT` con auto-resume **vuelve a encenderlo**. Por eso, al cerrar la sesión, mira Compute → Warehouses o corre de nuevo el `SUSPEND`.

---

### 3.5 Verificar (opcional, no cambia nada)

```sql
SHOW WAREHOUSES;
```

**Qué hace:** lista warehouses de la cuenta (nombre, tamaño, estado, owner).  
**Por qué:** confirmar `AMVA_WH` = X-Small, Suspended, y que no estamos usando el de Streamlit.  
**Analogía GIS:** el catálogo de “máquinas de geoproceso” disponibles, no el listado de feature classes.

```sql
DESC WAREHOUSE AMVA_WH;
```

**Qué hace:** describe propiedades de `AMVA_WH` (size, auto-suspend, generation, timeout).  
**Por qué:** auditoría: la UI y el SQL deben decir lo mismo.  
**Analogía GIS:** propiedades de la herramienta, no la tabla de atributos.

---

### Si el warehouse ya existe (creado en la UI)

Como el owner en pantalla es `ACCOUNTADMIN`, SYSADMIN puede necesitar permiso de uso. Corre esto **solo si** `USE WAREHOUSE AMVA_WH` con SYSADMIN falla:

```sql
USE ROLE ACCOUNTADMIN;

GRANT USAGE, OPERATE ON WAREHOUSE AMVA_WH TO ROLE SYSADMIN;

USE ROLE SYSADMIN;
```

**Qué hace:** `USAGE` permite elegir el warehouse; `OPERATE` permite suspender/reanudar. Luego regresas a SYSADMIN.  
**Por qué:** creaste el objeto con ACCOUNTADMIN. El trabajo diario no debe quedarse en ese rol.  
**Analogía GIS:** el admin de dominio te da permiso de usar el servidor de geoproceso; tú no trabajas todo el día como domain admin.

**No incluye contraseñas.** La contraseña del usuario vive en Snowsight y, en dbt, en la env var `SNOWFLAKE_PASSWORD`. El YAML de conexión es `profiles.yml` **en esta carpeta** (gitignored), no un secreto en GitHub.

---

## 4. SQL de database y schemas medallón (BRONZE, SILVER, GOLD)

Esto **ya está corrido** en Workspaces (`Untitled.sql`, warehouse `AMVA_WH` X-Small). Es el “feature dataset” del proyecto. Crear base y schema es metadato; aun así el SQL puede reanudar `AMVA_WH` — suspende al terminar. El `SELECT` confirmó el identifier **`NVSMAZV-BE58602`**.

**Medallón (una frase cada uno):**

| Schema | Qué guarda | Analogía GIS |
|--------|------------|----------------|
| **BRONZE** | Carga cruda (anonimizada). Casi como llegó el Excel. | Shapefile / CAD de campo, sin limpiar. |
| **SILVER** | Staging dbt: tipos, nombres, grano, tests. | Capas proyectadas, campos estándar, join limpio. |
| **GOLD** | Marts para el tablero (grano tarea, grano trámite/mapa). | Mapas publicados / servicios que lee el visor. |

dbt: `source` (Bronze) → `stg_` (Silver) → `int_horas_habiles` (Silver) → `mart_tareas_sgc` (Gold, grano tarea) → `mart_tramites_geo` (Gold, grano trámite). El tablero **no** consulta Snowflake: `scripts/04_export_dashboard_json.py` baja Gold a `dashboard/data/tramites.json` + `tareas.json`; Leaflet lee esos archivos. Perímetro urbano: `scripts/05_pack_map_assets.py` (FileGDB → GeoJSON WGS84 + PNG). Visor: [`dashboard/index.html`](../dashboard/index.html).

```sql
USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS AMVA_ENV;

CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;

SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME() AS account_identifier;
```

**Qué hace el bloque completo:** crea la base `AMVA_ENV`, tres schemas, y devuelve el identificador de cuenta para `profiles.yml` / dbt.  
**Por qué:** un solo “contenedor” de analítica, separado de bases de ejemplo de Snowflake.  
**Analogía GIS:** creas una geodatabase `AMVA_ENV` con tres feature datasets (Bronce, Plata, Oro). El `SELECT` es leer el nombre del servidor para conectarte desde otra herramienta.

Desglose:

```sql
CREATE DATABASE IF NOT EXISTS AMVA_ENV;
```

**Qué hace:** crea la base de datos si no existe.  
**Por qué:** `AMVA_ENV` = environmental permits. No usamos `SNOWFLAKE_SAMPLE_DATA` para el proyecto.  
**Analogía GIS:** *New File Geodatabase*.

```sql
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;
```

**Qué hace:** tres namespaces dentro de la misma base.  
**Por qué:** medallón explícito. Bronze no se mezcla con el mart del mapa.  
**Analogía GIS:** tres feature datasets. El visor (tablero) solo debería “publicar” Gold.

```sql
SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME() AS account_identifier;
```

**Qué hace / por qué / analogía:** ver [sección 5](#5-cómo-leer-el-account-identifier).

### Comprobar schemas (ya existen)

```sql
SHOW SCHEMAS IN DATABASE AMVA_ENV;
```

**Qué hace:** lista schemas de `AMVA_ENV`. Debes ver `BRONZE`, `SILVER`, `GOLD` (y `PUBLIC` / `INFORMATION_SCHEMA` que Snowflake crea solo).  
**Por qué:** verificar el DDL antes de cargar datos.  
**Analogía GIS:** listar feature datasets de la GDB.

### Sesión de trabajo (cuando toque consultar datos)

```sql
USE WAREHOUSE AMVA_WH;
USE DATABASE AMVA_ENV;
USE SCHEMA AMVA_ENV.BRONZE;
```

**Qué hace:** fija motor, base y schema de la sesión. `USE WAREHOUSE` **puede reanudar** `AMVA_WH` si `AUTO_RESUME` está en TRUE.  
**Por qué:** los `SELECT` necesitan un warehouse; el DDL de create database no es el que “paga” de verdad, el `dbt build` sí.  
**Analogía GIS:** eliges el PC de geoproceso, abres la GDB y te metes al dataset Bronze.

Al terminar: `ALTER WAREHOUSE AMVA_WH SUSPEND;`

**Frase B2:** "Bronze is raw, Silver is cleaned, Gold is what the dashboard reads."

---

## 5. Cómo leer el account identifier

Snowsight (capturas 01–07):

```text
https://app.snowflake.com/nvsmazv/be58602/
```

| Trozo de la URL | Significado |
|-----------------|-------------|
| `nvsmazv` | **Organization name** |
| `be58602` | **Account name** |

El identificador que piden dbt, SnowSQL y muchos drivers es:

```text
<organizacion>-<cuenta>
```

**Confirmado por el `SELECT` (SUCCESS, 1 row, 99 ms)** — no es solo la URL; es el valor que devolvió Snowflake:

```text
NVSMAZV-BE58602
```

Esa cadena va a `profiles.yml` **en la raíz de este proyecto** (gitignored; dbt la lee con `--profiles-dir`). El SQL que se corrió:

```sql
SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME() AS account_identifier;
```

**Qué hace:** concatena organización y cuenta con un guion. Eso es el *account identifier* moderno.  
**Por qué:** `profiles.yml` (en esta carpeta, gitignored) necesita `account:` para que dbt se conecte. La URL de Snowsight ya lo muestra partido en dos, pero el SQL es la fuente de verdad.  
**Analogía GIS:** el “nombre del servidor” + “nombre de la GDB” para el `.sde` / la conexión. No es la contraseña.

**No confundir con:**

- `CURRENT_ACCOUNT()` → *account locator* viejo (otro formato). Prefiere org + account name.
- La URL `….snowflakecomputing.com` → a veces usa locator. dbt Core con `account: org-cuenta` es lo habitual hoy.

**Qué salió:** una sola columna `ACCOUNT_IDENTIFIER` = **`NVSMAZV-BE58602`**. Esa cadena va a `profiles.yml` en esta carpeta. El archivo **no** se sube a GitHub (`.gitignore`). La plantilla `profiles.yml.example` sí.

Usuario de conexión para dbt: **`jfgarci206`** (`CURRENT_USER`), no el display name `JOSE GARCIA`. Rol en `profiles.yml`: **SYSADMIN** (trabajo diario). El dropdown de Snowsight puede seguir en ACCOUNTADMIN; eso no es el rol de dbt. **Contraseña: no se documenta aquí** — vive en la variable de entorno `SNOWFLAKE_PASSWORD`.

**Frase B2:** "The account identifier is organization-name dash account-name. I do not put the password in GitHub."

---

## 6. SQL dbt: horas hábiles y mart SGC

**Estado 15 sep 2026:** horas hábiles validadas en Snowsight (RUN 6 / RUN 7). Mart trámite: `dbt run --select mart_tramites_geo` SUCCESS; `dbt test --select mart_tramites_geo` → 4 PASS.

| Modelo | Schema | Grano | Materialización |
|--------|--------|--------|-----------------|
| `stg_permisos` / `stg_dias_nolaborables` | SILVER | tarea / fecha no laborable | view (ya existían) |
| `int_horas_habiles` | SILVER | 1 fila = 1 tarea | view |
| `mart_tareas_sgc` | GOLD | 1 fila = 1 tarea | view (trial: no copia tabla) |
| `mart_tramites_geo` | GOLD | 1 fila = 1 trámite | view (trial: no copia tabla) |

`+schema: GOLD` no concatena `SILVER_GOLD` gracias a `macros/generate_schema_name.sql`.

### Fórmula (HorasTotales DAX → SQL)

Jornada AMVA **07:30–17:30** (10 h). Día hábil = lunes–viernes (`DAYOFWEEKISO` 1–5) **y** la fecha **no** está en `stg_dias_nolaborables`. El Excel ya trae sábados/domingos, pero le faltan 21 fines de semana en el rango: el filtro ISO es obligatorio. No hay doble resta: de `DIAS_NOLABORABLES` solo se restan festivos de **lunes a viernes** en el tramo intermedio.

- Falta INICIO o FIN → `horas_habiles` NULL.
- FIN <= INICIO → 0.
- Mismo día → intersección del intervalo con 07:30–17:30 (0 si el día no es hábil).
- Varios días → horas del primer día (inicio → 17:30) + 10 × (lun–vie estrictamente entre medio − festivos lun–vie) + horas del último día (07:30 → fin).
- `dias_habiles` = horas / 10. `dias_habiles_mix` = COALESCE(cerrado, hasta ahora), como `DiasHabiles_Mix` en DAX.

SQL vivo: [`amva_pipeline/models/intermediate/int_horas_habiles.sql`](../amva_pipeline/models/intermediate/int_horas_habiles.sql). Macros: `n_lun_a_vie`, `horas_parciales_laborales`, `horas_habiles_intervalo`.

**Qué hace:** calcula el tiempo neto de cada tarea sin noches, fines de semana ni festivos.  
**Por qué:** todos los KPI de SGC (`DiasHabiles_*`) dependen de esta columna; si está mal, el tablero miente.  
**Analogía GIS:** es un “erase” del calendario no hábil sobre la línea de tiempo, no un dissolve del trámite.

`mart_tareas_sgc` añade `contar_dias_habiles` (réplica V2: desde Auto de Inicio o Actuación Jurídica; si hay `fecha_decide`, la tarea debe iniciar y terminar en o antes) y deja `estado_sgc` / `agrupacion_sgc` de DECIDE. **No** se replica `SGC_Modificado_v7`: esa cadena usa `FUNCIONARIO` (PII, ya fuera).

**Frase B2:** "Business hours are 7:30 to 17:30. I subtract nights, weekends and Colombian holidays. One row is still one task."

Comprobación en Workspaces (una sentencia por Run): [`docs/sql/workspaces_bootstrap.sql`](sql/workspaces_bootstrap.sql) RUN 6, RUN 7 y RUN 8.

**RUN 6 (usuario, SUCCESS):** `FILAS=216414`, `CON_HORAS=214483`, `AVG_HORAS_HABILES=49.59`.  
**RUN 7 (usuario, SUCCESS):** 5 tareas del trámite `1391640` (Firmas 0.013 h; En Espera de Requerimientos 83.62 h / 8.36 días hábiles). Trial **$400 / $400**.

### Mart trámite (`mart_tramites_geo`)

**Qué hace:** una fila por `tramite_id`. Suma `horas_habiles` / `dias_habiles` de las tareas con `contar_dias_habiles = 'SI'`. Copia municipio, clasificación, estado, decisión y SGC nativo de la última tarea. Lat/lon solo si DECIDE trae un punto (trámite o visita) dentro del Valle de Aburrá (lat 5.9–6.6, lon −75.7 a −75.3). Si no hay GPS usable, `latitud`/`longitud` quedan NULL; el municipio se conserva. **No se inventan coordenadas.**

**Por qué:** el mapa y los KPI de permiso no pueden leer 216k tareas. Grano trámite ≠ grano tarea.

**Analogía GIS:** dissolve de tareas a permiso + join espacial solo con puntos reales; no pones el centroide del municipio “porque sí”.

**Frase B2:** "One Gold row is one permit. The map uses real DECIDE coordinates. If there is no GPS, latitude stays null."

Export (sin PII): `python scripts/04_export_dashboard_json.py` → `dashboard/data/tramites.json` (trámites + KPI + grupos) y `dashboard/data/tareas.json` (historial compacto). El visor [`dashboard/index.html`](../dashboard/index.html) solo hace `fetch` de esos archivos; no hay contraseñas ni llamadas al warehouse.

RUN 8 (esperar ~4025 trámites, ~1182 con coordenadas, 19 municipios distintos, avg ~111 días hábiles SGC):

```sql
SELECT
    COUNT(*) AS tramites,
    COUNT(latitud) AS con_coordenadas,
    COUNT(DISTINCT municipio) AS municipios,
    ROUND(AVG(dias_habiles_sgc), 2) AS avg_dias_habiles_sgc
FROM AMVA_ENV.GOLD.MART_TRAMITES_GEO;
```

**RUN 8 (usuario, SUCCESS):** `TRAMITES=4025`, `CON_COORDENADAS=1182`, `MUNICIPIOS=19`, `AVG_DIAS_HABILES_SGC=111.02`. Trial **$400 / $400**. Warehouse `AMVA_WH`.

Queda fuera: Airflow, CI. Cómo abrir el HTML: [sección 13](#13-tablero-html-leaflet).

---

## 7. Doble destino: Snowflake trial y DuckDB

El SQL de dbt (cuando exista) es **el mismo modelo mental**: `source` → `stg` → marts. El *adapter* cambia. Ya hay **dos outputs** en el perfil `amva_pipeline`:

| Destino | Para qué | Límite |
|---------|----------|--------|
| **Snowflake trial** (`--target snowflake`) | Demostrar warehouse, roles, medallón en la nube, entrevista Factored. Account `NVSMAZV-BE58602`, warehouse `AMVA_WH`, database `AMVA_ENV`, schema `SILVER`. | La cuenta trial **caduca**. Datos en Snowflake se pierden. |
| **DuckDB** (`--target duckdb`) | Correr el **mismo SQL dbt** en el laptop, $0, sin créditos. Archivo: `data/processed/amva.duckdb`. | No es el warehouse oficial de **este** repo; es el plan B cuando expire el trial. |

**Qué queda cuando expire el trial:** el SQL en **GitHub** (este informe + futuros `models/*.sql`). No el storage de Snowflake.

**Frase B2:** "The same dbt SQL can run on DuckDB later. When the trial expires, GitHub still has the SQL."

DuckDB no sustituye Airflow ni el tablero. El tablero sigue leyendo JSON exportado desde Gold, no una conexión live.

---

## 8. Frases B2 cortas para la entrevista

Usar en inglés, cortas, sin inventar producción:

1. "Snowflake stores data and runs SQL. Credits are billed while the warehouse is running."
2. "I created AMVA_WH as X-Small, Gen1, auto-suspend 60 seconds. I do not use the Streamlit warehouse."
3. "This trial has no COMPUTE_WH. I use SYSADMIN for daily work, not ACCOUNTADMIN."
4. "Bronze is raw, Silver is cleaned, Gold feeds the dashboard."
5. "The dashboard reads Gold as JSON. It does not query Snowflake from the browser."
6. "dbt is the transformation layer. Airflow is the orchestrator. I will add Airflow at the end, locally."
7. "Azure Data Factory is the Azure equivalent of Airflow. I practiced Airflow, not ADF in production."
8. "The same dbt SQL can run on DuckDB. The trial data expires; the GitHub SQL remains."
9. "I remove PII before load. That is Law 1581, not optional."
10. "Grain matters: a task row is not the same as a permit row on the map."
11. "My Snowflake login is jfgarci206. dbt uses SYSADMIN, not ACCOUNTADMIN. The password is an environment variable, not in GitHub."

Mapeo Airflow ↔ ADF (cuando toque la clase de orquestación): DAG → Pipeline; Task → Activity; Connection → Linked Service; Schedule → Trigger.

---

## 9. Capturas Snowsight

Carpeta: [`docs/screenshots/`](screenshots/). Inventario en [`docs/screenshots/README.md`](screenshots/README.md). **Ninguna captura debe mostrar la contraseña.**

| Archivo | Qué demuestra |
|---------|----------------|
| `00-snowflake-signup-company.png` | Formulario de registro (opcional). |
| `01-snowsight-home-trial-400.png` | Home. `JOSE GARCIA`, `ACCOUNTADMIN`, **$400 of $400**, trial **30 days**, URL `app.snowflake.com/nvsmazv/be58602/`. No pulsar Upgrade. |
| `02-warehouses-learning-wh-suspended.png` | **No hay `COMPUTE_WH`**. Solo `SNOWFLAKE_LEARNING_WH` y `SYSTEM$STREAMLIT_NOTEBOOK_WH` (Suspended). |
| `03-new-warehouse-dialog.png` | Diálogo por defecto: Standard **Gen2**, auto-suspend **5 min** (se cambió). |
| `04-new-warehouse-amva-wh-settings.png` | Valores reales: Standard **Gen1**, X-Small, auto-suspend **1 min**, 1 crédito/hora, sin multi-cluster, sin query acceleration. |
| `05-amva-wh-created-started.png` | `AMVA_WH` creado, estado **Started** (1/1). Había que suspender. |
| `06-amva-wh-resumed-15s.png` | `AMVA_WH` reanudado hace 15 s, constraint **`STANDARD_GEN_1`**. |
| `07-amva-wh-suspended.png` | Los **3** warehouses **Suspended**. Listo para el DDL de `AMVA_ENV`. |
| `08-workspaces-welcome.png` | **Welcome to Workspaces.** Se abrió **SQL file**. No Notebook, Streamlit ni dbt Project de Snowflake. |
| `09-sql-role-warehouse-picker.png` | `Untitled.sql`. Rol UI **ACCOUNTADMIN**, warehouse **`AMVA_WH` (X-Small)**. |
| `10-sql-create-amva-env.png` | SQL pegado: `USE ROLE SYSADMIN` + `CREATE DATABASE AMVA_ENV` + BRONZE/SILVER/GOLD + `SELECT` identifier. |
| `11-account-identifier-nvsmazv-be58602.png` | Resultado SUCCESS: `ACCOUNT_IDENTIFIER` = **`NVSMAZV-BE58602`**. Sin contraseñas. |
| `12-current-user-jfgarci206.png` | Resultado SUCCESS: `USUARIO` = **`jfgarci206`**, `ROL` = **`ACCOUNTADMIN`**. Login name para dbt. Dropdown UI sigue ACCOUNTADMIN; warehouse `AMVA_WH`. Sin contraseñas. |
| `13-raw-dias-nolaborables.png` | Explorador: `Bases de datos AMVA\raw` con `DIAS_NOLABORABLES.xlsx` + extractos DECIDE (gitignored). |

---

## 10. profiles.yml en esta carpeta (gitignored)

### 10.1 SQL que identificó el usuario de conexión

En Workspaces (`Untitled.sql`) se corrió:

```sql
SELECT CURRENT_USER() AS usuario, CURRENT_ROLE() AS rol;
```

**Qué hace:** `CURRENT_USER()` es el **login name** de Snowflake (el que pide `profiles.yml` en `user:`). `CURRENT_ROLE()` es el rol **de esa sesión SQL**, no necesariamente el que dbt usará.  
**Por qué:** el display name de la UI es `JOSE GARCIA`; dbt no se conecta con el nombre bonito, se conecta con `jfgarci206`.  
**Analogía GIS:** el alias del mapa no es el usuario del `.sde`. El `.sde` pide el login del servidor.

**Qué salió (SUCCESS, 1 row, 56 ms):** `usuario` = **`jfgarci206`**, `rol` = **`ACCOUNTADMIN`**. Captura: [`12-current-user-jfgarci206.png`](screenshots/12-current-user-jfgarci206.png).

El archivo SQL también tiene `USE ROLE SYSADMIN;` arriba. Si solo se selecciona y corre el último `SELECT`, ese `USE ROLE` **no se ejecuta** y `CURRENT_ROLE()` sigue siendo el del dropdown (**ACCOUNTADMIN**). Eso no está mal para *descubrir el usuario*; para dbt el rol se fija en `profiles.yml` como **SYSADMIN**, no ACCOUNTADMIN.

**Frase B2:** "CURRENT_USER is the login name. dbt uses SYSADMIN, not ACCOUNTADMIN."

---

### 10.2 Por qué `profiles.yml` no va a Git (sí vive en ESTA carpeta)

El `profiles.yml` de trabajo está **aquí**, no en `C:\Users\Usuario\.dbt\`:

```text
D:\PROJECTS-ANALITYICS ENGINEER\AMVA PROJECTS\amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW\profiles.yml
```

dbt, por defecto, busca `~/.dbt/`. En este proyecto se fuerza esta carpeta:

```text
dbt debug --target snowflake --profiles-dir "D:\PROJECTS-ANALITYICS ENGINEER\AMVA PROJECTS\amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW"
```

(o `$env:DBT_PROFILES_DIR` = esa misma ruta). Git **no** lo versiona: está en `.gitignore`. La plantilla `profiles.yml.example` sí.

| Archivo | ¿Git? | Qué es |
|---------|-------|--------|
| `profiles.yml` (raíz de este proyecto) | **No** | Perfil de trabajo. Password = env var, no texto claro. |
| [`profiles.yml.example`](../profiles.yml.example) | **Sí** | Misma estructura, password = `env_var`, sin secreto. |
| `.gitignore` | Sí | Ignora `profiles.yml` y **no** ignora `profiles.yml.example` (`!profiles.yml.example`). |

**Analogía GIS:** compartes el toolbox (ModelBuilder) en GitHub. El archivo de conexión al enterprise GDB (usuario + password) se queda en tu PC. Si lo subes, cualquiera clona tus llaves.

La contraseña **no** se escribe en el YAML. dbt la lee en runtime:

```yaml
password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
```

**Qué hace:** Jinja `env_var` pide la variable de entorno `SNOWFLAKE_PASSWORD`. Si no existe, `dbt debug` falla (esperado hasta que el usuario la defina en su terminal).  
**Por qué:** un archivo en disco con password en claro se copia, se respalda y se filtra. Una env var vive en la sesión de PowerShell.  
**Analogía GIS:** no guardas la password del `.sde` dentro del MXD que mandas por correo; la pides al abrir la conexión.

**Nunca** pegar la contraseña en el chat, en este informe ni en GitHub. El usuario la escribe **solo** en su terminal.

---

### 10.3 YAML del perfil (para entenderlo; igual que el `.example`)

El `name:` de `dbt_project.yml` debe coincidir con la clave de arriba del YAML. Aquí ambos son `amva_pipeline`.

```yaml
amva_pipeline:
  target: snowflake
  outputs:
    snowflake:
      type: snowflake
      account: NVSMAZV-BE58602
      user: jfgarci206
      role: SYSADMIN
      warehouse: AMVA_WH
      database: AMVA_ENV
      schema: SILVER
      threads: 4
      client_session_keep_alive: False
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
    duckdb:
      type: duckdb
      path: "D:/PROJECTS-ANALITYICS ENGINEER/AMVA PROJECTS/amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW/data/processed/amva.duckdb"
      threads: 4
```

| Clave | Valor | Qué hace / por qué |
|-------|--------|---------------------|
| `amva_pipeline` | nombre del perfil | Debe ser igual a `profile:` en `dbt_project.yml`. Si no coincide, `dbt debug` no encuentra el perfil. |
| `target: snowflake` | destino por defecto | `dbt debug` usa Snowflake salvo que pases `--target duckdb`. |
| `type: snowflake` | adapter | Instala `dbt-snowflake`. No es HTTP path (eso era Databricks). |
| `account` | `NVSMAZV-BE58602` | Identifier org-cuenta. Ver [sección 5](#5-cómo-leer-el-account-identifier). |
| `user` | `jfgarci206` | Login name (`CURRENT_USER`). No `JOSE GARCIA`. |
| `role` | `SYSADMIN` | Rol de la sesión dbt. **No** ACCOUNTADMIN. Crear objetos de analítica es trabajo de SYSADMIN. |
| `warehouse` | `AMVA_WH` | Motor XS del proyecto. No usar el warehouse de Streamlit. |
| `database` | `AMVA_ENV` | La GDB de analítica (medallón). |
| `schema` | `SILVER` | Schema por defecto de dbt. Hoy está bien escribir staging aquí. No usamos `+schema` todavía: el macro por defecto concatenaría `SILVER_gold`. |
| `threads` | `4` | Consultas en paralelo. 4 es razonable en XS. |
| `client_session_keep_alive` | `False` | No mantiene la sesión viva “por si acaso”; ayuda a que el warehouse se suspenda. |
| `password` | `env_var(...)` | Ver 10.2. **No hay password real en ningún archivo.** |
| `duckdb.path` | `data/processed/amva.duckdb` | Segundo motor, archivo local. $0. El trial caduca; este archivo (y el SQL en Git) no. |

**Analogía GIS:** `account` + `user` + `role` + `warehouse` + `database` + `schema` = servidor + login + rol + PC de geoproceso + GDB + feature dataset. DuckDB es una file geodatabase en el disco C:.

**Frase B2:** "profiles.yml lives in this project folder. Git ignores it. The password is an environment variable."

`dbt debug` se corre **desde** `amva_pipeline` con `--profiles-dir` a la raíz de este repo. El `~\.dbt\profiles.yml` de esta laptop puede existir por otro proyecto; **este** repo no depende de esa ruta.

---

### 10.4 Esqueleto dbt en el repo (sin SQL de negocio)

```text
profiles.yml              → trabajo (gitignored; --profiles-dir a esta carpeta)
profiles.yml.example      → plantilla (sí va a git)
amva_pipeline/dbt_project.yml
amva_pipeline/models/staging/sources.yml   → stub bronze.dias_nolaborables
amva_pipeline/models/marts/.gitkeep
requirements.txt          → dbt-snowflake y dbt-duckdb (>=1.9, <2.0)
```

`dbt_project.yml`: `name` y `profile` = `amva_pipeline`; staging materializa **view**; marts materializa **table**. Suficiente para `dbt debug`. **No** hay `stg_*.sql` inventados.

`dbt debug` **no se corrió** contra Snowflake en esta sesión. El usuario define `SNOWFLAKE_PASSWORD` en PowerShell y usa `--profiles-dir` a esta carpeta.

---

## 11. Calendario DIAS_NOLABORABLES (motor de DiasHabiles)

**Una línea:** todo cálculo de `DiasHabiles` / `HorasTotales` (jornada 7:30–17:30) **debe** excluir sábados, domingos y las fechas de `DIAS_NOLABORABLES.xlsx`. No es opcional. El SQL ya vive en `int_horas_habiles` (sección 6). `WEEKDAY_NUM` 6 = sábado, 7 = domingo; 1–5 = festivo entre semana. El extracto llega a 2025-11-30 (1180 filas); después de esa fecha el SQL sigue quitando fines de semana.

Archivo exacto: `Bases de datos AMVA/raw/DIAS_NOLABORABLES.xlsx` (gitignored). Source dbt: `source('bronze', 'dias_nolaborables')`. Columna de join: `D_DIA` → `fecha_no_laborable`.

---

## Apéndice — script único (copiar al SQL file de Workspaces)

Orden: rol → crear o alterar warehouse → suspender → base y schemas → identifier. Si `AMVA_WH` ya existe, el `CREATE IF NOT EXISTS` no hace daño; el `ALTER` alinea. Suspende **siempre** al final. El bloque de `AMVA_ENV` + `SELECT` **ya se ejecutó** en Workspaces (`Untitled.sql`).

```sql
-- AMVA: warehouse + medallion DB (SYSADMIN)
-- No pegar passwords. Suspender al terminar.

USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS AMVA_WH
  WAREHOUSE_SIZE = 'XSMALL'
  WAREHOUSE_TYPE = STANDARD
  GENERATION = '1'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 300
  COMMENT = 'AMVA dbt - XS, auto-suspend 60s';

ALTER WAREHOUSE AMVA_WH SET
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 300;

ALTER WAREHOUSE AMVA_WH SUSPEND;

CREATE DATABASE IF NOT EXISTS AMVA_ENV;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;

SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME() AS account_identifier;

SHOW WAREHOUSES;
SHOW SCHEMAS IN DATABASE AMVA_ENV;
```

**Qué hace:** deja la cuenta en el estado objetivo del proyecto (XS Gen1 suspendido + `AMVA_ENV` medallón) y muestra identifier + catálogo.  
**Por qué:** un solo copiar/pegar para reproducir lo de la UI y el siguiente DDL.  
**Analogía GIS:** un ModelBuilder de “preparar GDB y apagar el PC de geoproceso”.

Si `GRANT` hace falta, usa el bloque ACCOUNTADMIN de la sección 3 **antes** de trabajar con SYSADMIN.

---

---

## 12. Cómo se conecta dbt de verdad (lo que funcionó y por qué demoró)

**Estado:** 15 sep 2026, 22:03. `dbt debug` → **All checks passed!**  
SQL numerado (RUN 1–5) también en [`docs/sql/workspaces_bootstrap.sql`](sql/workspaces_bootstrap.sql). **No** ejecutar ese archivo de un solo Run.  
**Qué es cada cosa (no confundir):**

| Objeto | Nombre | Oficio |
|--------|--------|--------|
| Account identifier | `NVSMAZV-BE58602` | Servidor. No es la contraseña. |
| Warehouse | `AMVA_WH` | Motor XS. **No** es la database. Compute → Warehouses. |
| Database | `AMVA_ENV` | GDB. Databases → explorer. |
| Schemas | `BRONZE` / `SILVER` / `GOLD` | Feature datasets. |
| User de Snowsight | Google / `JFGARCI206@GMAIL.COM` | Solo la UI web. |
| User de dbt | `AMVA_DBT` | Login nativo + password. |
| Role dbt | `SYSADMIN` | Hay que `GRANT ROLE` a `AMVA_DBT`. |

**Regla de Workspaces (la que nos hizo perder horas):** el editor **compila todo el archivo a la vez**. Si en el mismo Run pones `CREATE DATABASE AMVA_ENV` y `CREATE SCHEMA AMVA_ENV.BRONZE`, Snowflake busca `AMVA_ENV` **antes** de crearla y dice *does not exist*. El botón Run a veces ejecuta **solo la última sentencia**. Por eso `CREATE USER` y `GRANT ROLE` hay que hacerlos **solos**, de a uno.

### Receta que sí funcionó (copiar en este orden)

**1.** Warehouse `AMVA_WH` en la UI: XS, Gen1, auto-suspend 1 min, Suspended. No Upgrade.

**2.** SQL file, rol ACCOUNTADMIN, warehouse `AMVA_WH`. **Un Run:**

```sql
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS AMVA_ENV;
```

**3.** **Otro Run** (ya existe la base):

```sql
USE ROLE ACCOUNTADMIN;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.BRONZE;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.SILVER;
CREATE SCHEMA IF NOT EXISTS AMVA_ENV.GOLD;
```

**4.** **Otro Run** (usuario dbt; no uses `jfgarci206` ni el email):

```sql
USE ROLE ACCOUNTADMIN;
CREATE USER AMVA_DBT PASSWORD = 'AmvaDbt2026' MUST_CHANGE_PASSWORD = FALSE;
```

**5.** **Otro Run:**

```sql
USE ROLE ACCOUNTADMIN;
GRANT ROLE SYSADMIN TO USER AMVA_DBT;
```

**6.** **Otro Run** (objetos ya existen):

```sql
USE ROLE ACCOUNTADMIN;
GRANT USAGE ON WAREHOUSE AMVA_WH TO ROLE SYSADMIN;
GRANT USAGE ON DATABASE AMVA_ENV TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.BRONZE TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.SILVER TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA AMVA_ENV.GOLD TO ROLE SYSADMIN;
```

**7.** Laptop: `pip install dbt-snowflake`. `profiles.yml` en **esta** carpeta (`user: AMVA_DBT`, `database: AMVA_ENV`). Desde `amva_pipeline`:

```powershell
dbt debug --target snowflake --profiles-dir "D:\PROJECTS-ANALITYICS ENGINEER\AMVA PROJECTS\amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW"
```

### Por qué demoró (errores reales)

| Error | Qué creímos | Qué era |
|-------|-------------|---------|
| `Could not find adapter type snowflake` | YAML malo | Faltaba `pip install dbt-snowflake` en el mismo Python. |
| 390100 username/password | Account mal / clave de Gmail | 1) Pegamos el texto de ejemplo `esa-clave-de-snowsight`. 2) Snowsight es Google; `jfgarci206` **no** tiene password nativa. 3) `$env:SNOWFLAKE_PASSWORD` no estaba en esa ventana. |
| 390190 SAML Identity Provider | Seguir con `externalbrowser` | Esta trial **no** tiene IdP SAML para dbt. El Config File de Snowsight miente para este caso. |
| `User JFGARCI206 does not exist` | ALTER USER al CURRENT_USER | El login web es el email; para dbt hay que **crear** `AMVA_DBT`. |
| `Database AMVA_ENV does not exist` en el mismo script que CREATE | La base “era” `AMVA_WH` | Warehouse ≠ database. Además Workspaces **compila** `CREATE SCHEMA AMVA_ENV.…` antes de crear la DB. |
| `User AMVA_DBT does not exist` tras un script largo | CREATE USER había corrido | Run ejecutó el **último** GRANT, no el CREATE. |
| 390186 SYSADMIN not granted | Password otra vez | Faltaba `GRANT ROLE SYSADMIN TO USER AMVA_DBT` **solo**, en su propio Run. |

**Lo que no hay que hacer:** `authenticator: externalbrowser`; clave de Gmail; meter password en GitHub; un solo SQL gigante en Workspaces; confundir Compute con Databases.

**Frase B2:** "Snowsight uses Google login. dbt uses a dedicated Snowflake user with a native password. Workspaces compiles the whole file, so I create the database, then schemas, then the user, one run at a time."

---

## 13. Tablero HTML (Leaflet)

Pipeline: **Gold (Snowflake) → Python (`scripts/04_export_dashboard_json.py`) → JSON/GeoJSON/PNG en `dashboard/data/` → `index.html`**. El navegador nunca llama a Snowflake.

| Pieza | Archivo |
|--------|---------|
| Visor | [`dashboard/index.html`](../dashboard/index.html) |
| Trámites + KPI + grupos | `dashboard/data/tramites.json` |
| Historial de tareas | `dashboard/data/tareas.json` |
| Perímetro urbano WGS84 | `dashboard/data/perimetro_urbano_amva.geojson` |
| Basemap empaquetado | `dashboard/assets/satelite-aburra.jpg` + `dashboard/data/basemap-bounds.json` |
| Leaflet local | `dashboard/vendor/leaflet/` |
| Marca AMVA | `dashboard/assets/` |

Perímetro: capa `PerimetroUrbanoAMVA_25072025` del FileGDB → WGS84 (`scripts/05_pack_map_assets.py`). El fondo es un JPEG satelital local (`L.imageOverlay`); el HTML no pide teselas a Esri/OSM/Google.

**Cómo abrir (no usar `file://`):**

```powershell
python -m http.server 8000 --directory dashboard
```

Luego **http://localhost:8000**.

**Cómo enviar:** comprima la carpeta `dashboard/` (HTML + `data/` + `vendor/` + `assets/`) y ábrala igual, con un servidor estático. Sin `file://` el `fetch` de JSON suele fallar.

**Frase B2:** "The dashboard reads Gold as JSON. It does not query Snowflake from the browser."

---

*Fin del corte 15-sep-2026. RUN 6/7/8 validados. Mart trámite + JSON + HTML Leaflet. Falta Airflow y CI. User `AMVA_DBT`.*
