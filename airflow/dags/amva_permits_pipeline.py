"""Pipeline AMVA: Bronze (opcional) → dbt Silver/Gold → JSON del tablero.

Se crea PAUSADO para no encender el warehouse XS sin querer.
Trigger manual en la UI, o unschedule semanal si hay créditos.

Ingest Excel (216k filas) NO corre en el schedule: solo si
Variable Airflow `amva_run_ingest` = true.
"""
from __future__ import annotations

import os
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator

PROJECT = os.environ.get("AMVA_PROJECT_DIR", "/opt/airflow/project")
PROFILES = os.environ.get("DBT_PROFILES_DIR", PROJECT)
DBT_DIR = f"{PROJECT}/amva_pipeline"

default_args = {
    "owner": "amva",
    "retries": 0,
    "execution_timeout": timedelta(hours=2),
}


def _ingest_enabled(**_context) -> bool:
    return str(Variable.get("amva_run_ingest", default_var="false")).lower() in {
        "1",
        "true",
        "yes",
        "si",
        "sí",
    }


def _choose_ingest_branch(**_context) -> str:
    if _ingest_enabled():
        return "bronze_dias_nolaborables"
    return "skip_ingest"


with DAG(
    dag_id="amva_permits_pipeline",
    description="DECIDE → Snowflake (dbt) → JSON geoportal AMVA",
    start_date=pendulum.datetime(2026, 9, 1, tz="America/Bogota"),
    schedule="0 6 * * 1",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["amva", "dbt", "snowflake"],
    is_paused_upon_creation=True,
    doc_md=__doc__,
) as dag:
    start = EmptyOperator(task_id="start")

    maybe_ingest = BranchPythonOperator(
        task_id="maybe_ingest_bronze",
        python_callable=_choose_ingest_branch,
    )

    load_calendar = BashOperator(
        task_id="bronze_dias_nolaborables",
        bash_command=f"cd '{PROJECT}' && python scripts/02_load_dias_nolaborables.py",
    )
    load_permisos = BashOperator(
        task_id="bronze_permisos",
        bash_command=f"cd '{PROJECT}' && python scripts/03_load_permisos_sample.py",
    )

    skip_ingest = EmptyOperator(task_id="skip_ingest")

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd '{DBT_DIR}' && dbt build --target snowflake "
            f"--profiles-dir '{PROFILES}' --select staging intermediate marts"
        ),
        trigger_rule="none_failed_min_one_success",
    )

    export_json = BashOperator(
        task_id="export_dashboard_json",
        bash_command=f"cd '{PROJECT}' && python scripts/04_export_dashboard_json.py",
    )

    pack_html = BashOperator(
        task_id="pack_standalone_html",
        bash_command=f"cd '{PROJECT}' && python scripts/07_pack_standalone_html.py",
    )

    end = EmptyOperator(task_id="end")

    start >> maybe_ingest
    maybe_ingest >> load_calendar >> load_permisos >> dbt_build
    maybe_ingest >> skip_ingest >> dbt_build
    dbt_build >> export_json >> pack_html >> end
