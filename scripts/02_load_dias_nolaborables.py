"""Carga DIAS_NOLABORABLES.xlsx -> AMVA_ENV.BRONZE.DIAS_NOLABORABLES.

Sin este calendario, HorasTotales / DiasHabiles no pueden replicar el DAX.
No carga el Excel DECIDE (PII, 45 MB). Eso es el siguiente script.

Uso (desde la raíz del repo):
  python scripts/02_load_dias_nolaborables.py
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yaml
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "Bases de datos AMVA" / "raw" / "DIAS_NOLABORABLES.xlsx"
PROFILES = ROOT / "profiles.yml"


def _snowflake_cfg() -> dict:
    data = yaml.safe_load(PROFILES.read_text(encoding="utf-8"))
    return data["amva_pipeline"]["outputs"]["snowflake"]


def _password(cfg: dict) -> str:
    raw = cfg.get("password")
    if raw is None or (isinstance(raw, str) and "env_var" in raw):
        pw = os.environ.get("SNOWFLAKE_PASSWORD")
        if not pw:
            raise RuntimeError("Defina SNOWFLAKE_PASSWORD en la sesión.")
        return pw
    return str(raw)


def main() -> None:
    if not XLSX.exists():
        raise FileNotFoundError(XLSX)

    df = pd.read_excel(XLSX, engine="openpyxl")
    df.columns = [str(c).upper() for c in df.columns]
    df["D_DIA"] = pd.to_datetime(df["D_DIA"]).dt.date

    cfg = _snowflake_cfg()
    conn = connect(
        account=cfg["account"],
        user=cfg["user"],
        password=_password(cfg),
        role=cfg["role"],
        warehouse=cfg["warehouse"],
        database=cfg["database"],
        schema="BRONZE",
    )
    try:
        conn.cursor().execute("USE SCHEMA AMVA_ENV.BRONZE")
        success, nchunks, nrows, _ = write_pandas(
            conn,
            df,
            table_name="DIAS_NOLABORABLES",
            database="AMVA_ENV",
            schema="BRONZE",
            auto_create_table=True,
            overwrite=True,
            quote_identifiers=False,
        )
        if not success:
            raise RuntimeError("write_pandas failed")
        print(f"OK BRONZE.DIAS_NOLABORABLES rows={nrows} chunks={nchunks}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
