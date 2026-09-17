# Airflow — pipeline AMVA

Un contenedor. SequentialExecutor. **Sin Astronomer ni costo.**

## Arranque

```powershell
cd airflow
copy .env.example .env
# Edite .env y ponga SNOWFLAKE_PASSWORD
docker compose up --build
```

UI: http://localhost:8081 — usuario `admin`, contraseña `admin`.

El DAG `amva_permits_pipeline` nace **pausado**. En la entrevista: Unpause → Trigger.

## Qué hace

1. `maybe_ingest_bronze` — solo si Variable `amva_run_ingest` = `true` (carga Excel a Bronze).
2. `dbt_build` — staging → intermediate (horas hábiles) → marts Gold.
3. `export_dashboard_json` — Gold → `dashboard/data/*.json`.
4. `pack_standalone_html` — HTML único para enviar.

El schedule (lunes 06:00) no corre hasta que quite la pausa. Así no se gasta el trial XS.

## Variable de ingest

Admin → Variables → `amva_run_ingest` = `true` solo cuando vaya a recargar el Excel.
