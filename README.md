# AMVA — permisos y licencias ambientales

Pipeline de analytics engineering para el Área Metropolitana del Valle de Aburrá:
**Excel DECIDE → Snowflake (Bronze / Silver / Gold) → dbt → Geoportal Leaflet.**

Cuenta de Snowflake de prueba (XS, auto-suspend 60 s). Airflow corre en Docker local, sin Astronomer.

Repo: [jfgarci2-amva-permits-analytics_Snowflake_Dbt_Airflow](https://github.com/jfgarci2/jfgarci2-amva-permits-analytics_Snowflake_Dbt_Airflow)

## Qué hay aquí

| Capa | Dónde | Qué |
| --- | --- | --- |
| Bronze | `AMVA_ENV.BRONZE` | Excel anonimizado (sin `CODFUNCIONARIO` / `FUNCIONARIO` / `TERCERO`, Ley 1581) + calendario `DIAS_NOLABORABLES` |
| Silver | `amva_pipeline/models/staging` + `intermediate` | Limpieza y **horas hábiles en SQL** (jornada 7:30–17:30, lun–vie, festivos) |
| Gold | `models/marts` | `MART_TAREAS_SGC` (216 414 tareas) y `MART_TRAMITES_GEO` (4 025 trámites, 1 182 con GPS) |
| Tablero | `dashboard/` | Geoportal Leaflet (foto local + Esri si hay red) |
| Orquestación | `airflow/` | DAG pausado; un contenedor; puerto 8081 |
| CI | `.github/workflows/ci.yml` | ¿está bien? `dbt parse` en DuckDB — **no enciende el warehouse** |
| CD | `.github/workflows/cd.yml` | publícalo: geoportal en GitHub Pages. Snowflake solo a mano |

Los grupos de trabajo del mapa salen de la cadena SGC v0–v7 (Power BI), no de `GRUPO` año-tipo ni de `ESTADO_SGC` crudo.

## dbt (local)

```powershell
copy profiles.yml.example profiles.yml
$env:SNOWFLAKE_PASSWORD = "su-password"
$env:DBT_PROFILES_DIR = (Get-Location).Path
cd amva_pipeline
dbt debug --target snowflake
dbt build --target snowflake --select staging intermediate marts
```

`profiles.yml` está gitignored. El password va en `SNOWFLAKE_PASSWORD`, no en Git.

## Airflow (local, $0)

Hace falta Docker Desktop. El DAG **nace pausado**: no hay corrida automática contra Snowflake.

```powershell
cd airflow
copy .env.example .env
# Edite .env: SNOWFLAKE_PASSWORD=...
docker compose up --build
```

UI: http://localhost:8081 — `admin` / `admin`.

1. Unpause `amva_permits_pipeline`.
2. Trigger DAG.
3. El ingest de Excel (216 k filas) **no corre** salvo Variable `amva_run_ingest` = `true`.

Detalle: [`airflow/README.md`](airflow/README.md).

## GitHub Actions (mismo esquema que catastro Medellín)

**CI** (`ci.yml`) — cada pull request / push a `main`:

- lint SQL/Python (no bloquea)
- `dbt parse` con DuckDB en memoria (`ci/profiles.yml`)
- sintaxis de `scripts/` y del DAG

**CD** (`cd.yml`) — cuando entra a `main`:

- publica `dashboard/` en GitHub Pages
- **no** corre `dbt build` en Snowflake (el trial XS). Gold lo orquesta Airflow.

`dbt build` en Snowflake solo si dispara CD a mano y marca *run_snowflake*. Secret: `SNOWFLAKE_PASSWORD`.

## Tablero

```powershell
python -m http.server 8000 --directory dashboard
```

http://127.0.0.1:8000/

HTML único para enviar (foto embebida, sin servidor):

```powershell
python scripts/07_pack_standalone_html.py
```

2 843 trámites no tienen GPS: salen en búsqueda / ficha, no se inventa un centroide.

## PII

Nunca en Gold, JSON ni Git: `CODFUNCIONARIO`, `FUNCIONARIO`, `TERCERO`. `FUNCIONARIO` solo se usa en RAM para SGC v7 (firmas) y no se persiste.
