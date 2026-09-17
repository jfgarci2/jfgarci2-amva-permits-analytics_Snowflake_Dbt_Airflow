"""Convierte shapefiles AMVA a GeoJSON WGS84 para el geoportal (sin geopandas)."""
from __future__ import annotations

import json
from pathlib import Path

import pyogrio.raw
from pyproj import Transformer
from shapely import from_wkb
from shapely.geometry import mapping
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[1]
SHP = ROOT / "Shapefiles"
OUT = ROOT / "dashboard" / "data" / "capas"
BBOX = (-75.70, 6.04, -75.28, 6.52)


def _write(name: str, fc: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OK {name} features={len(fc['features'])} {path.stat().st_size/1024:.0f} KB")


def _read(src: Path, columns: list[str] | None = None):
    meta, _fids, wkbs, fields = pyogrio.raw.read(src, force_2d=True, columns=columns)
    names = [f[0] if isinstance(f, (list, tuple)) else f for f in meta["fields"]]
    to4326 = Transformer.from_crs(meta["crs"], 4326, always_xy=True)
    to3857 = Transformer.from_crs(4326, 3857, always_xy=True)
    inv3857 = Transformer.from_crs(3857, 4326, always_xy=True)
    return names, fields, wkbs, to4326, to3857, inv3857


def _props(names, fields, i, keep):
    out = {}
    for j, n in enumerate(names):
        if n not in keep:
            continue
        v = fields[j][i]
        if v is None:
            continue
        try:
            if v != v:  # NaN
                continue
        except Exception:
            pass
        out[n] = v.item() if hasattr(v, "item") else v
    return out


def convert_polys(src: Path, keep: list[str], simplify_m: float, out_name: str):
    names, fields, wkbs, to4326, to3857, inv3857 = _read(src, keep)
    feats = []
    for i, wkb in enumerate(wkbs):
        geom = from_wkb(bytes(wkb))
        geom = shp_transform(lambda x, y, z=None: to4326.transform(x, y), geom)
        if simplify_m:
            g3857 = shp_transform(lambda x, y, z=None: to3857.transform(x, y), geom)
            geom = shp_transform(lambda x, y, z=None: inv3857.transform(x, y), g3857.simplify(simplify_m))
        if geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        if maxx < BBOX[0] or minx > BBOX[2] or maxy < BBOX[1] or miny > BBOX[3]:
            continue
        feats.append(
            {"type": "Feature", "properties": _props(names, fields, i, keep), "geometry": mapping(geom)}
        )
    _write(out_name, {"type": "FeatureCollection", "features": feats})


def convert_redrio(src: Path):
    names, fields, wkbs, to4326, to3857, inv3857 = _read(src, ["RIO", "N_QUEBRADA"])
    feats, labels = [], []
    n_rio = names.index("RIO") if "RIO" in names else None
    n_nom = names.index("N_QUEBRADA") if "N_QUEBRADA" in names else None
    for i, wkb in enumerate(wkbs):
        geom = from_wkb(bytes(wkb))
        geom = shp_transform(lambda x, y, z=None: to4326.transform(x, y), geom)
        minx, miny, maxx, maxy = geom.bounds
        if maxx < BBOX[0] or minx > BBOX[2] or maxy < BBOX[1] or miny > BBOX[3]:
            continue
        rio = int(fields[n_rio][i] or 0) if n_rio is not None else 0
        g3857 = shp_transform(lambda x, y, z=None: to3857.transform(x, y), geom)
        geom = shp_transform(
            lambda x, y, z=None: inv3857.transform(x, y), g3857.simplify(20 if rio == 1 else 50)
        )
        if geom.is_empty:
            continue
        nom = str(fields[n_nom][i]) if n_nom is not None and fields[n_nom][i] else None
        props = {"RIO": rio}
        if nom and nom != "None":
            props["N_QUEBRADA"] = nom
        feats.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})
        if rio == 1 and nom and nom != "None":
            c = geom.representative_point()
            labels.append(
                {
                    "type": "Feature",
                    "properties": {"N_QUEBRADA": nom},
                    "geometry": {"type": "Point", "coordinates": [round(c.x, 6), round(c.y, 6)]},
                }
            )
    _write("red_hidrica.geojson", {"type": "FeatureCollection", "features": feats})
    _write(
        "red_hidrica_labels.geojson",
        {"type": "FeatureCollection", "features": labels[:60]},
    )


def main():
    convert_polys(
        SHP / "Capas Geograficas" / "MunicipiosAMVA.shp",
        ["MpNombre", "MpCodigo"],
        8,
        "municipios_amva.geojson",
    )
    convert_polys(
        SHP / "Capas Geograficas" / "PerimetroUrbanoAMVA_U.shp",
        ["MUNICIPIO"],
        8,
        "perimetro_urbano_amva.geojson",
    )
    convert_redrio(SHP / "Red hidrica" / "Red hidrica" / "RedRio.shp")


if __name__ == "__main__":
    main()
