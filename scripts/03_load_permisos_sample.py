"""DECIDE -> Bronze PERMISOS, sin PII (Ley 1581).

Carga el archivo completo. SAMPLE_ROWS=None o 0 = todas las filas.
Fuente: QRY_PERMISOSAMBIENTALES_DECIDE_31082026.xlsx

Las columnas de fecha se convierten a datetime en pandas (serial Excel o
datetime nativo) ANTES de write_pandas, para que Snowflake reciba
TIMESTAMP_NTZ y no NUMBER. overwrite=True (reemplaza, no append).
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yaml
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

ROOT = Path(__file__).resolve().parents[1]
XLSX = (
    ROOT
    / "Bases de datos AMVA"
    / "raw"
    / "QRY_PERMISOSAMBIENTALES_DECIDE_31082026.xlsx"
)
PROFILES = ROOT / "profiles.yml"
PII_COLS = ("CODFUNCIONARIO", "FUNCIONARIO", "TERCERO")
# None o 0 = archivo completo. Entero > 0 = muestra (solo para pruebas).
SAMPLE_ROWS = None
SHEET = "QRY_PERMISOSAMBIENTALES_DECIDE"
CHUNK_SIZE = 10_000
DATE_COLS = (
    "INICIOTRAMITE",
    "TERMINATRAMITE",
    "INICIATAREA",
    "FINALIZATAREA",
    "FECHARADICADOSINA",
    "FECHADECIDE",
    "FECHAAUTOINICIO",
)


def _cfg() -> dict:
    return yaml.safe_load(PROFILES.read_text(encoding="utf-8"))["amva_pipeline"][
        "outputs"
    ]["snowflake"]


def _password(cfg: dict) -> str:
    raw = cfg.get("password")
    if raw is None or (isinstance(raw, str) and "env_var" in raw):
        pw = os.environ.get("SNOWFLAKE_PASSWORD")
        if not pw:
            raise RuntimeError("Defina SNOWFLAKE_PASSWORD en la sesión.")
        return pw
    return str(raw)


def _excel_or_dt(series: pd.Series) -> pd.Series:
    """Datetime nativo, serial Excel (días desde 1899-12-30) o epoch ns/ms."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    if pd.api.types.is_numeric_dtype(series):
        nonempty = series.dropna()
        if nonempty.empty:
            return pd.to_datetime(series, errors="coerce")
        mx = float(nonempty.abs().max())
        if mx > 1e17:
            return pd.to_datetime(series, unit="ns", errors="coerce")
        if mx > 1e14:
            return pd.to_datetime(series, unit="us", errors="coerce")
        if mx > 1e11:
            return pd.to_datetime(series, unit="ms", errors="coerce")
        if mx > 1e9:
            return pd.to_datetime(series, unit="s", errors="coerce")
        return pd.to_datetime(series, unit="D", origin="1899-12-30", errors="coerce")

    return pd.to_datetime(series, errors="coerce")


def _snowflake_type(col: str, series: pd.Series) -> str:
    if col in DATE_COLS or pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP_NTZ"
    if pd.api.types.is_integer_dtype(series):
        return "NUMBER(38,0)"
    if pd.api.types.is_float_dtype(series):
        return "FLOAT"
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    return "VARCHAR"


def _create_table_sql(df: pd.DataFrame) -> str:
    cols = [f"    {c} {_snowflake_type(c, df[c])}" for c in df.columns]
    return (
        "CREATE OR REPLACE TABLE AMVA_ENV.BRONZE.PERMISOS (\n"
        + ",\n".join(cols)
        + "\n)"
    )


def main() -> None:
    if not XLSX.exists():
        raise FileNotFoundError(XLSX)

    read_kwargs: dict = {"sheet_name": SHEET, "engine": "openpyxl"}
    if SAMPLE_ROWS:
        read_kwargs["nrows"] = int(SAMPLE_ROWS)
        print(f"LEYENDO MUESTRA nrows={SAMPLE_ROWS}")
    else:
        print("LEYENDO ARCHIVO COMPLETO (SAMPLE_ROWS=None)")

    df = pd.read_excel(XLSX, **read_kwargs)
    excel_rows = len(df)
    drop = [c for c in PII_COLS if c in df.columns]
    df = df.drop(columns=drop)
    df.columns = [str(c).upper() for c in df.columns]

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = _excel_or_dt(df[col])

    cfg = _cfg()
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
        cur = conn.cursor()
        cur.execute("USE WAREHOUSE AMVA_WH")
        cur.execute("USE SCHEMA AMVA_ENV.BRONZE")
        cur.execute("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 1200")
        ddl = _create_table_sql(df)
        print(ddl)
        cur.execute(ddl)
        ok, nchunks, nrows, _ = write_pandas(
            conn,
            df,
            table_name="PERMISOS",
            database="AMVA_ENV",
            schema="BRONZE",
            auto_create_table=False,
            overwrite=False,
            quote_identifiers=False,
            chunk_size=CHUNK_SIZE,
            use_logical_type=True,
        )
        if not ok:
            raise RuntimeError("write_pandas failed")
        cur.execute("SELECT COUNT(*) FROM AMVA_ENV.BRONZE.PERMISOS")
        bronze_rows = cur.fetchone()[0]
        print(
            f"OK BRONZE.PERMISOS excel_rows={excel_rows} "
            f"write_pandas_rows={nrows} bronze_count={bronze_rows} "
            f"dropped_pii={drop} chunks={nchunks} sample_rows={SAMPLE_ROWS}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
