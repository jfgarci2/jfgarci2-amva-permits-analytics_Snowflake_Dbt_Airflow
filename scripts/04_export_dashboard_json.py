"""Exporta Gold → JSON compacto para el tablero estático.

Una sesión de warehouse. El navegador nunca habla con Snowflake.
Sin PII (funcionario, tercero, codfuncionario).

Fuentes:
  GOLD.MART_TRAMITES_GEO  (grano trámite: KPI + GPS real)
  GOLD.MART_TAREAS_SGC    (grano tarea: historial + grupo)

Grupo de trabajo = SGC_Modificado_v7 (DAX AMVA, portado en
scripts/sgc_modificado.py). Se une desde data/processed/sgc_modificado_v7.parquet
(generado con el Excel; FUNCIONARIO solo en RAM). Si no hay parquet, se
calcula con TAREA + PROCESOTAREA + ESTADOSGC (sin listas de Firmas).

Uso (raíz del repo, misma conexión que 02/03):
  python scripts/06_build_sgc_modificado.py
  python scripts/04_export_dashboard_json.py

Salida:
  dashboard/data/tramites.json
  dashboard/data/tareas.json
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml
from snowflake.connector import connect

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles.yml"
DATA = ROOT / "dashboard" / "data"
SGC_PARQUET = ROOT / "data" / "processed" / "sgc_modificado_v7.parquet"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sgc_modificado import grupo_trabajo_v7, norm_tarea  # noqa: E402

SQL_TRAMITES = """
SELECT
    tramite_id,
    municipio,
    clasificacion_permiso,
    estado_tramite,
    decision,
    estado_sgc,
    agrupacion_sgc,
    n_tareas,
    n_tareas_sgc,
    horas_habiles_sgc,
    dias_habiles_sgc,
    latitud,
    longitud,
    origen_coordenada
FROM AMVA_ENV.GOLD.MART_TRAMITES_GEO
"""

SQL_TAREAS = """
SELECT
    tramite_id,
    tarea_id,
    tarea_orden,
    tarea_nombre,
    proceso_tarea,
    proceso,
    grupo,
    agrupacion_sgc,
    horas_habiles,
    dias_habiles,
    fecha_inicia_tarea,
    fecha_finaliza_tarea,
    contar_dias_habiles,
    estado_tarea,
    estado_sgc
FROM AMVA_ENV.GOLD.MART_TAREAS_SGC
"""


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


def _round(value, digits=2):
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return round(float(value), digits)


def _coord(value):
    v = _round(value, 6)
    return v


def _txt(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    s = str(value).strip()
    return s or None


_SMALL = {
    "a", "al", "de", "del", "el", "en", "la", "las", "los", "o", "para", "por", "u", "y",
}

_MUN_FIXED = {
    "medellin": "Medellín",
    "itagui": "Itagüí",
    "itagüi": "Itagüí",
    "bello": "Bello",
    "envigado": "Envigado",
    "sabaneta": "Sabaneta",
    "la estrella": "La Estrella",
    "caldas": "Caldas",
    "copacabana": "Copacabana",
    "girardota": "Girardota",
    "barbosa": "Barbosa",
}


def _fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _title_es(raw) -> str | None:
    s = _txt(raw)
    if not s:
        return None
    parts = re.split(r"(\s+|/|-)", s.strip())
    out = []
    word_i = 0
    for part in parts:
        if not part or part.isspace() or part in "-/":
            out.append(part)
            continue
        low = part.lower()
        if word_i > 0 and low in _SMALL:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:] if low else low)
        word_i += 1
    return "".join(out)


def _label_municipio(raw) -> str:
    s = _txt(raw)
    if not s:
        return "Sin municipio"
    s = re.sub(r"^M\d+\s*[-–—:]\s*", "", s, flags=re.I).strip()
    if not s:
        return "Sin municipio"
    folded = _fold(s)
    if "fuera" in folded and "metropolitana" in folded:
        return "Fuera del Área Metropolitana"
    if folded in {"estrella"}:
        return "La Estrella"
    if folded.replace(" ", "") in {"-", ".", "-.", "-.-"}:
        return "Sin municipio"
    titled = _title_es(s) or "Sin municipio"
    return _MUN_FIXED.get(_fold(titled), titled)


def _label_grupo(raw) -> str:
    s = _txt(raw)
    if not s or _fold(s).replace("_", " ") in {"sin grupo", "ninguno", "na", "n/a"}:
        return "Sin grupo"
    return _title_es(s) or "Sin grupo"


def _grupo_familia(raw) -> str:
    """Quita el prefijo AAAA- de GRUPO SGC_Modificado para KPI y filtros."""
    s = _label_grupo(raw)
    m = re.match(r"^\d{4}\s*[-–]\s*(.+)$", s)
    fam = (m.group(1).strip() if m else s) or "Sin grupo"
    return fam if fam else "Sin grupo"


def _intern(table: dict[str, int], order: list[str], value) -> int | None:
    s = _txt(value)
    if s is None:
        return None
    idx = table.get(s)
    if idx is None:
        idx = len(order)
        table[s] = idx
        order.append(s)
    return idx


def _iso_min(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d %H:%M")


def _pick_grupo(g: pd.DataFrame) -> object:
    vals = [_txt(v) for v in g["grupo_lbl"].tolist()]
    filled = [v for v in vals if v and v != "Sin grupo"]
    if not filled:
        return "Sin grupo"
    counts = Counter(filled)
    top = counts.most_common(1)[0][1]
    winners = {k for k, n in counts.items() if n == top}
    if len(winners) == 1:
        return next(iter(winners))
    last = g.sort_values(["tarea_orden"], kind="mergesort").iloc[-1]
    return _txt(last["grupo_lbl"]) or "Sin grupo"


def _assign_grupo_sgc(tareas: pd.DataFrame) -> pd.DataFrame:
    proc_col = "proceso_tarea" if "proceso_tarea" in tareas.columns else "proceso"
    if SGC_PARQUET.exists():
        sgc_map = pd.read_parquet(SGC_PARQUET)
        sgc_map.columns = [c.lower() for c in sgc_map.columns]
        for col in ("tramite_id", "tarea_orden"):
            tareas[col] = pd.to_numeric(tareas[col], errors="coerce").astype("Int64")
            sgc_map[col] = pd.to_numeric(sgc_map[col], errors="coerce").astype("Int64")
        tareas["tarea_norm"] = tareas["tarea_nombre"].map(norm_tarea)
        n0 = len(tareas)
        sgc_map = sgc_map.drop_duplicates(
            ["tramite_id", "tarea_orden", "tarea_norm"], keep="first"
        )
        tareas = tareas.merge(
            sgc_map[["tramite_id", "tarea_orden", "tarea_norm", "grupo_sgc"]],
            on=["tramite_id", "tarea_orden", "tarea_norm"],
            how="left",
        )
        if len(tareas) != n0:
            raise RuntimeError(f"merge SGC duplicó filas {n0} -> {len(tareas)}")
        miss = tareas["grupo_sgc"].isna() | (tareas["grupo_sgc"].astype(str).str.strip() == "")
        if miss.any():
            tareas.loc[miss, "grupo_sgc"] = [
                grupo_trabajo_v7(n, p, None, e)
                for n, p, e in zip(
                    tareas.loc[miss, "tarea_nombre"],
                    tareas.loc[miss, proc_col],
                    tareas.loc[miss, "estado_sgc"],
                )
            ]
        tareas["grupo_lbl"] = tareas["grupo_sgc"].fillna("Sin grupo")
        return tareas.drop(columns=["grupo_sgc", "tarea_norm"], errors="ignore")
    tareas["grupo_lbl"] = [
        grupo_trabajo_v7(n, p, None, e)
        for n, p, e in zip(tareas["tarea_nombre"], tareas[proc_col], tareas["estado_sgc"])
    ]
    return tareas


def _json_dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str),
        encoding="utf-8",
    )


def main() -> None:
    cfg = _cfg()
    conn = connect(
        account=cfg["account"],
        user=cfg["user"],
        password=_password(cfg),
        role=cfg["role"],
        warehouse=cfg["warehouse"],
        database=cfg["database"],
        schema="GOLD",
    )
    try:
        cur = conn.cursor()
        cur.execute("USE WAREHOUSE AMVA_WH")
        cur.execute("USE SCHEMA AMVA_ENV.GOLD")
        cur.execute(SQL_TRAMITES)
        tramites = cur.fetch_pandas_all()
        cur.execute(SQL_TAREAS)
        tareas = cur.fetch_pandas_all()
    finally:
        conn.close()

    tramites.columns = [c.lower() for c in tramites.columns]
    tareas.columns = [c.lower() for c in tareas.columns]
    tramites["municipio_lbl"] = tramites["municipio"].map(_label_municipio)
    tareas = _assign_grupo_sgc(tareas)
    tareas["agr_lbl"] = tareas["agrupacion_sgc"].map(
        lambda v: _title_es(v) or "Sin agrupación"
    )
    tareas["sgc_lbl"] = tareas["estado_sgc"].map(
        lambda v: _title_es(v) or "Sin unidad SGC"
    )
    tareas["proceso_lbl"] = tareas["proceso"].map(lambda v: _title_es(v))
    tareas["nombre_lbl"] = tareas["tarea_nombre"].map(lambda v: _title_es(v))
    tareas["estado_lbl"] = tareas["estado_tarea"].map(lambda v: _title_es(v))

    d_m, d_g, d_a, d_c, d_e, d_p, d_et, d_o = {}, {}, {}, {}, {}, {}, {}, {}
    o_m, o_g, o_a, o_c, o_e, o_p, o_et, o_o = [], [], [], [], [], [], [], []

    grupo_by_id: dict = {}
    agr_mode_by_id: dict = {}
    for tid, g in tareas.groupby("tramite_id", sort=False):
        grupo_by_id[tid] = _pick_grupo(g)
        agrs = [
            v
            for v in g["sgc_lbl"].tolist()
            if v and v != "Sin unidad SGC"
        ]
        agr_mode_by_id[tid] = Counter(agrs).most_common(1)[0][0] if agrs else None

    sgc = tareas[tareas["contar_dias_habiles"].astype(str).str.upper() == "SI"]
    grp_rows = []
    for name, g in tareas.groupby("grupo_lbl", dropna=False):
        name = name or "Sin grupo"
        ids = g["tramite_id"].unique()
        g_sgc = sgc.loc[sgc.index.intersection(g.index)]
        gps_n = int(
            tramites.loc[
                tramites["tramite_id"].isin(ids) & tramites["latitud"].notna(),
                "tramite_id",
            ].nunique()
        )
        grp_rows.append(
            {
                "g": name,
                "nt": int(len(g)),
                "ntr": int(len(ids)),
                "gps": gps_n,
                "ah": _round(g["horas_habiles"].mean()),
                "ad": _round(g["dias_habiles"].mean()),
                "ahs": _round(g_sgc["horas_habiles"].mean()) if len(g_sgc) else None,
                "ads": _round(g_sgc["dias_habiles"].mean()) if len(g_sgc) else None,
            }
        )
    grp_rows.sort(key=lambda r: (-r["ntr"], r["g"]))

    t_rows = []
    for rec in tramites.itertuples(index=False):
        tid = rec.tramite_id
        grupo = grupo_by_id.get(tid)
        agr = agr_mode_by_id.get(tid) or _title_es(rec.agrupacion_sgc)
        lat = _coord(rec.latitud)
        lon = _coord(rec.longitud)
        t_rows.append(
            [
                int(tid) if pd.notna(tid) else None,
                _intern(d_m, o_m, rec.municipio_lbl),
                _intern(d_g, o_g, grupo),
                _intern(d_a, o_a, agr),
                _intern(d_c, o_c, _title_es(rec.clasificacion_permiso)),
                _intern(d_e, o_e, _title_es(rec.estado_tramite)),
                int(rec.n_tareas) if pd.notna(rec.n_tareas) else 0,
                int(rec.n_tareas_sgc) if pd.notna(rec.n_tareas_sgc) else 0,
                _round(rec.horas_habiles_sgc),
                _round(rec.dias_habiles_sgc),
                lat,
                lon,
                _intern(d_o, o_o, rec.origen_coordenada),
            ]
        )

    grupos_out = []
    for row in grp_rows:
        grupos_out.append(
            {
                "i": _intern(d_g, o_g, row["g"]),
                "g": row["g"],
                "nt": row["nt"],
                "ntr": row["ntr"],
                "gps": row["gps"],
                "ah": row["ah"],
                "ad": row["ad"],
                "ahs": row["ahs"],
                "ads": row["ads"],
            }
        )

    n_gps = int(tramites["latitud"].notna().sum())
    payload_tr = {
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "src": ["AMVA_ENV.GOLD.MART_TRAMITES_GEO", "AMVA_ENV.GOLD.MART_TAREAS_SGC"],
        "nota_geo": (
            f"{n_gps} de {len(tramites)} trámites tienen GPS real de DECIDE "
            "(Valle de Aburrá). No se inventan coordenadas."
        ),
        "kpis": {
            "n": int(len(tramites)),
            "gps": n_gps,
            "mun": int(tramites["municipio_lbl"].nunique(dropna=True)),
            "avg_d": _round(tramites["dias_habiles_sgc"].mean()),
            "avg_h": _round(tramites["horas_habiles_sgc"].mean()),
            "nt": int(len(tareas)),
            "ng": int(sum(1 for r in grupos_out if r["g"] != "Sin grupo")),
        },
        "d": {
            "m": o_m,
            "g": o_g,
            "a": o_a,
            "c": o_c,
            "e": o_e,
            "o": o_o,
        },
        "grupos": grupos_out,
        "t": t_rows,
    }

    nombres, n_map = [], {}
    x = {}
    for tid, g in tareas.groupby("tramite_id", sort=False):
        g = g.sort_values(["tarea_orden"], kind="mergesort")
        rows = []
        for rec in g.itertuples(index=False):
            rows.append(
                [
                    int(rec.tarea_orden) if pd.notna(rec.tarea_orden) else None,
                    _intern(n_map, nombres, rec.nombre_lbl),
                    _iso_min(rec.fecha_inicia_tarea),
                    _iso_min(rec.fecha_finaliza_tarea),
                    _round(rec.horas_habiles),
                    _round(rec.dias_habiles),
                    _intern(d_g, o_g, rec.grupo_lbl),
                    _intern(d_a, o_a, rec.agr_lbl),
                    _intern(d_p, o_p, rec.proceso_lbl),
                    1 if _txt(rec.contar_dias_habiles) == "SI" else 0,
                    _intern(d_et, o_et, rec.estado_lbl),
                ]
            )
        x[str(int(tid))] = rows

    payload_ta = {
        "n": nombres,
        "g": o_g,
        "a": o_a,
        "p": o_p,
        "e": o_et,
        "x": x,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    p_tr = DATA / "tramites.json"
    p_ta = DATA / "tareas.json"
    _json_dump(p_tr, payload_tr)
    _json_dump(p_ta, payload_ta)

    old = DATA / "mart_tramites.json"
    if old.exists():
        old.unlink()

    mb_tr = p_tr.stat().st_size / (1024 * 1024)
    mb_ta = p_ta.stat().st_size / (1024 * 1024)
    sample = "1391640" in x
    print(
        f"OK tramites={len(t_rows)} tareas={len(tareas)} gps={n_gps} "
        f"grupos={len(grupos_out)} sample_1391640={sample} "
        f"tramites.json={mb_tr:.2f}MB tareas.json={mb_ta:.2f}MB"
    )
    if mb_tr + mb_ta > 20:
        print("WARN combined JSON > 20MB")


if __name__ == "__main__":
    main()
