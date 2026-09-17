"""Calcula SGC_Modificado_v7 desde el Excel DECIDE (FUNCIONARIO solo en RAM).

Salida sin PII:
  data/processed/sgc_modificado_v7.parquet
    tramite_id, tarea_orden, tarea_norm, grupo_sgc

Uso (raíz del repo):
  python scripts/06_build_sgc_modificado.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sgc_modificado import grupo_trabajo_v7, norm_tarea  # noqa: E402

XLSX = (
    ROOT
    / "Bases de datos AMVA"
    / "raw"
    / "QRY_PERMISOSAMBIENTALES_DECIDE_31082026.xlsx"
)
OUT = ROOT / "data" / "processed" / "sgc_modificado_v7.parquet"
COLS = [
    "CODTRAMITE",
    "CODTAREA",
    "ORDEN",
    "TAREA",
    "PROCESOTAREA",
    "FUNCIONARIO",
    "ESTADOSGC",
]


def main() -> None:
    if not XLSX.exists():
        raise FileNotFoundError(XLSX)
    print(f"LEYENDO {XLSX.name} (solo columnas SGC)")
    df = pd.read_excel(XLSX, sheet_name="QRY_PERMISOSAMBIENTALES_DECIDE", usecols=COLS)
    df["grupo_sgc"] = [
        grupo_trabajo_v7(t, p, f, e)
        for t, p, f, e in zip(
            df["TAREA"], df["PROCESOTAREA"], df["FUNCIONARIO"], df["ESTADOSGC"]
        )
    ]
    out = pd.DataFrame(
        {
            "tramite_id": pd.to_numeric(df["CODTRAMITE"], errors="coerce").astype("Int64"),
            "tarea_orden": pd.to_numeric(df["ORDEN"], errors="coerce").astype("Int64"),
            "tarea_norm": df["TAREA"].map(norm_tarea),
            "grupo_sgc": df["grupo_sgc"],
        }
    )
    n_raw = len(out)
    out = out.drop_duplicates(["tramite_id", "tarea_orden", "tarea_norm"], keep="first")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    vc = out["grupo_sgc"].value_counts(dropna=False)
    print(f"OK {len(out)} filas (raw={n_raw}) -> {OUT}")
    print(vc.to_string())
    n_sin = int((out["grupo_sgc"] == "Sin grupo").sum())
    print(f"sin_grupo={n_sin} cubiertos={len(out) - n_sin}")


if __name__ == "__main__":
    main()
