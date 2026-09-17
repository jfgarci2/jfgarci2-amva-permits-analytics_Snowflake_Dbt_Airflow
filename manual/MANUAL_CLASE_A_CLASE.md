# Manual clase a clase — AMVA (Snowflake + dbt + Airflow)

Cuaderno corto. El **SQL completo con explicación** vive en [`docs/INFORME_TECNICO.md`](../docs/INFORME_TECNICO.md). Aquí no se duplica el informe.

**Quién:** José Fernando García. Entrevista Factored (Fátima), inglés B2.  
**Regla:** no subir `.env`, passwords ni Excel crudo con PII.

---

## Clase 1 — Oral (sin instalar nada)

Conceptos a poder decir en una frase:

| Término | Una línea |
|---------|-----------|
| Staging | Capa Silver: limpia Bronze, no cambia el grano. |
| `ref()` | dbt apunta a otro modelo; no hardcodees el nombre de tabla. |
| Ephemeral | Intermedio que no materializa tabla; vive en el SQL compilado. |
| Tests | Reglas (`unique`, `not_null`, relaciones). `dbt build` = run + test. |
| `run` vs `build` | `run` materializa; `build` materializa y testea. |
| Grain | Qué es **una fila**. Tarea ≠ trámite ≠ punto en el mapa. |
| Medallón | Bronze crudo → Silver limpio → Gold para el visor. |
| Snowflake | Guarda y computa. Cobra el **warehouse encendido**. |
| dbt | Transforma (ModelBuilder). |
| Airflow | Agenda (ADF en Azure es el equivalente; aquí no hay ADF). |
| Tablero HTML | Lee JSON de Gold. **No** consulta Snowflake desde el browser. |

**Frase B2:** "Snowflake stores. dbt transforms. Airflow schedules. The dashboard only draws JSON."

---

## Clase 2 — Cuenta Snowflake + warehouse + DB

**Hecho en la UI (15 sep 2026):** trial $400 / 30 días, usuario `JOSE GARCIA`, `ACCOUNTADMIN`, URL `app.snowflake.com/nvsmazv/be58602/`. Warehouse `AMVA_WH` = Standard **Gen1**, X-Small, auto-suspend **60 s**, auto-resume, sin multi-cluster, sin query acceleration. Nació Started; ahora los 3 warehouses están **Suspended**. No hay `COMPUTE_WH`. No usar `SNOWFLAKE_LEARNING_WH` ni `SYSTEM$STREAMLIT_NOTEBOOK_WH`.

Capturas: `docs/screenshots/01-…` (home) hasta `07-amva-wh-suspended.png`.

Trabajo diario: **SYSADMIN**, no ACCOUNTADMIN. No pulsar **Upgrade**.

### SQL (copiar al Worksheet)

Explicación línea a línea: [informe §3–§5](../docs/INFORME_TECNICO.md).

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
```

**Qué debe salir:** `AMVA_WH` Suspended. **No** pegues CREATE DATABASE y CREATE SCHEMA en el mismo Run de Workspaces (compila todo y falla). Ver informe §12.

`GENERATION = '1'` es SQL válido (comillas obligatorias). En la UI se eligió Gen1 porque Gen2 cuesta más.

**Analogía GIS:** warehouse = PC de geoproceso (apágalo); database = GDB; schemas = feature datasets.

**Frase B2:** "Credits are billed while the warehouse is running, not for stored data."

---

## Clase 2b — `dbt debug` OK (15 sep 2026)

Snowsight entra con **Google**. dbt **no**. Usuario nativo **`AMVA_DBT`** + password en `profiles.yml` (gitignored). Workspaces: **un CREATE por Run**.

Receta y tabla de errores: [informe §12](../docs/INFORME_TECNICO.md#12-cómo-se-conecta-dbt-de-verdad-lo-que-funcionó-y-por-qué-demoró).

```powershell
cd "...\amva_pipeline"
dbt debug --target snowflake --profiles-dir "D:\PROJECTS-ANALITYICS ENGINEER\AMVA PROJECTS\amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW"
```

**Qué debe salir:** `Connection test: [OK]` y `All checks passed!`

---

## Clase 3 — Cómo llega un Excel de tu PC a Snowflake (Python vs SQL vs dbt)

**Hecho:** 1180 filas en `AMVA_ENV.BRONZE.DIAS_NOLABORABLES`. Vista `AMVA_ENV.SILVER.STG_DIAS_NOLABORABLES`. 4 tests PASS.

Snowflake **no tiene acceso a tu disco D:**. No “entra” a Windows. Tu laptop **abre una conexión HTTPS** a `NVSMAZV-BE58602.snowflakecomputing.com` (igual que el navegador a Snowsight) y **empuja** filas. Usuario `AMVA_DBT` + warehouse `AMVA_WH` (se enciende, cobra, se duerme).

**Analogía GIS:** el `.xlsx` es un shapefile en tu carpeta. Python es “Add Data + Copy Features” hacia la GDB corporativa en la red. Snowflake es esa GDB. dbt es ModelBuilder: no copia el shape; arma una **vista** (definición SQL) encima.

### Tres lenguajes, tres oficios

| Pieza | Tipo | Archivo | Qué hace |
|-------|------|---------|----------|
| Ingesta | **Python** | `scripts/02_load_dias_nolaborables.py` | Lee el Excel **local**, se autentica, **crea/llena la tabla** Bronze. |
| Transformación | **SQL** (plantilla Jinja) | `amva_pipeline/models/staging/stg_dias_nolaborables.sql` | Receta: `SELECT` + `CAST` + nombres. **No** lee el xlsx. |
| Orquestación ligera | **CLI Python** (dbt) | comando `dbt run` | Compila el `.sql` y se lo **manda** a Snowflake. Snowflake ejecuta el SQL. |

dbt **no es un motor**. Es un compilador + mensajero. El `SELECT` corre **dentro** de Snowflake.

### Qué hace el Python (ingesta)

```text
Excel en D:\...\raw\DIAS_NOLABORABLES.xlsx
        → pandas (openpyxl)  lee filas en RAM
        → snowflake.connector.connect(...)  login AMVA_DBT
        → write_pandas(...)  CREATE/REPLACE tabla + INSERT
        → AMVA_ENV.BRONZE.DIAS_NOLABORABLES  (1180 filas)
```

`connect()` usa account, user, password, role, warehouse de `profiles.yml` (gitignored). Eso es un **driver** (como un cliente ArcSDE / ODBC): habla el protocolo de Snowflake por internet.

### Qué hace el SQL / dbt (Silver)

```sql
select * from {{ source('bronze', 'dias_nolaborables') }}
```

`source(...)` se vuelve `AMVA_ENV.BRONZE.DIAS_NOLABORABLES`. dbt crea una **VIEW** en Silver: mismos datos, columnas en snake_case (`fecha_no_laborable`). Si abres la vista en Snowsight, Snowflake corre ese SQL **en la nube**. El Excel ya no participa.

**Frase B2:** "Python loads the Excel from my laptop into Bronze. dbt only sends SQL. Snowflake stores and computes. The warehouse must be running while we load or build."

### Qué no es

- No es que Cursor “tenga Snowflake adentro”.
- No es un API de DECIDE/Oracle.
- Airflow, más adelante, solo **programa** el mismo Python + `dbt run` cuando aparezca un Excel nuevo.

---

## Clase 5 — Horas hábiles (jornada 07:30–17:30)

**Hecho:** vistas `AMVA_ENV.SILVER.INT_HORAS_HABILES` y `AMVA_ENV.GOLD.MART_TAREAS_SGC`. `dbt run` 4 SUCCESS. 9 tests PASS (incluye unit test de la fórmula).

**Grano:** 1 fila = 1 tarea (igual que `stg_permisos`).

**Fórmula:** horas netas entre `fecha_inicia_tarea` y `fecha_finaliza_tarea` recortadas a 07:30–17:30, sin noches, sin sábados/domingos (`DAYOFWEEKISO` 1–5) y sin festivos de `stg_dias_nolaborables`. Varios días = primer día parcial + 10 h × días hábiles del medio + último día parcial. `dias_habiles` = horas / 10.

El Excel de no laborables **ya trae** fines de semana, pero le faltan algunos: no se puede omitir el filtro de lunes–viernes. Los sábados del Excel **no** se restan otra vez.

SQL: `amva_pipeline/models/intermediate/int_horas_habiles.sql`. Explicación larga: [informe §6](../docs/INFORME_TECNICO.md#6-sql-dbt-horas-hábiles-y-mart-sgc).

**Frase B2:** "Business hours are 7:30 to 17:30. One row is still one task."

### Qué debe salir en Snowsight (un Run por SELECT)

RUN 6 y RUN 7 en [`docs/sql/workspaces_bootstrap.sql`](../docs/sql/workspaces_bootstrap.sql). Warehouse `AMVA_WH`.

**Validado (usuario, 15 sep 2026):** RUN 6 = 216414 / 214483 / 49.59 h. RUN 7 = trámite 1391640 (Firmas 0.013 h; espera 83.62 h). Trial $400/$400.

---

## Clase 6 — Mart trámite + JSON del tablero

**Hecho:** vista `AMVA_ENV.GOLD.MART_TRAMITES_GEO`. Grano: **1 fila = 1 trámite**. `dbt run --select mart_tramites_geo` SUCCESS. 4 tests PASS (`unique`/`not_null` de `tramite_id`, `not_null` de conteos).

Enrolla horas/días de `mart_tareas_sgc` donde `contar_dias_habiles = 'SI'`. Municipio y lat/lon salen de DECIDE. Si no hay GPS dentro del Valle de Aburrá, lat/lon quedan NULL (no se inventa un punto). El tablero lee JSON exportado, no el warehouse: `python scripts/04_export_dashboard_json.py` → `dashboard/data/tramites.json` + `tareas.json`. Perímetro: `python scripts/05_pack_map_assets.py`. Fondo satelital local: `dashboard/assets/satelite-aburra.jpg` (`L.imageOverlay`, sin teselas de internet). Visor: [`dashboard/index.html`](../dashboard/index.html).

**Frase B2:** "One Gold row is one permit. The dashboard reads JSON, not 216 thousand tasks."

### Qué debe salir en Snowsight

RUN 8 (una sentencia) en [`docs/sql/workspaces_bootstrap.sql`](../docs/sql/workspaces_bootstrap.sql):

```sql
SELECT
    COUNT(*) AS tramites,
    COUNT(latitud) AS con_coordenadas,
    COUNT(DISTINCT municipio) AS municipios,
    ROUND(AVG(dias_habiles_sgc), 2) AS avg_dias_habiles_sgc
FROM AMVA_ENV.GOLD.MART_TRAMITES_GEO;
```

**Qué debe salir:** ~4025 trámites, ~1182 con coordenadas, 19 municipios, avg ~111.02.

**Validado (usuario, 15 sep 2026):** RUN 8 = `TRAMITES=4025`, `CON_COORDENADAS=1182`, `MUNICIPIOS=19`, `AVG_DIAS_HABILES_SGC=111.02`. Trial $400/$400.

### Cómo abrir el tablero

No usar `file://` (el navegador bloquea el JSON). Desde la raíz del repo:

```powershell
python -m http.server 8000 --directory dashboard
```

Abrir **http://localhost:8000**. Para enviarlo: comprima la carpeta `dashboard/` completa (`index.html`, `data/`, `vendor/`, `assets/`) y abra igual con un servidor estático.

---

## Clases siguientes

4. Excel DECIDE **completo** → Bronze `permisos` (**216414** filas) — **hecho**.  
5. `stg_permisos` + horas hábiles — **hecho**.  
6. Mart geo + export JSON + HTML Leaflet — **hecho**.  
7. Airflow local. GitHub Actions si hay tiempo.

**Doble destino:** el SQL dbt podrá correrse luego en DuckDB. El trial caduca; GitHub conserva el código.

