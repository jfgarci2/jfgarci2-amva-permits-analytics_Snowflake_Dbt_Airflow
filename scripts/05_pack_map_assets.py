"""Empaqueta perímetro urbano (FileGDB) + basemap PNG + Leaflet local.

Capa: PerimetroUrbanoAMVA_25072025 (MAGNA CTM12 → WGS84).
Relleno opcional del PNG: MunicipiosAMVA.

Uso (raíz del repo):
  python scripts/05_pack_map_assets.py
"""
from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import pyogrio
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import Transformer
from shapely import from_wkb
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[1]
GDB = ROOT / "Geodatabase" / "mapaurbano.gdb"
DATA = ROOT / "dashboard" / "data"
VENDOR = ROOT / "dashboard" / "vendor" / "leaflet"
LAYER_PERIM = "PerimetroUrbanoAMVA_25072025"
LAYER_MUN = "MunicipiosAMVA"
# Inventario: bbox WGS84 [minx, miny, maxx, maxy]
BBOX_WGS84 = (-75.665796, 6.068293, -75.319622, 6.450710)
LEAFLET_VER = "1.9.4"


def _as_geom(raw):
    if raw is None:
        return None
    if hasattr(raw, "geom_type"):
        return raw
    blob = bytes(raw) if not isinstance(raw, (bytes, bytearray)) else raw
    return from_wkb(blob)


def _read_geoms(layer: str):
    info = pyogrio.read_info(GDB, layer=layer)
    crs = info.get("crs") or "EPSG:9377"
    _meta, _fids, geometry, _fields = pyogrio.raw.read(
        GDB, layer=layer, force_2d=True, read_geometry=True
    )
    geoms = []
    for raw in geometry:
        g = _as_geom(raw)
        if g is None or g.is_empty:
            continue
        geoms.append(g)
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    out = [shp_transform(transformer.transform, g) for g in geoms]
    return out, crs, info


def _to_wgs84_featurecollection(geoms, name: str) -> dict:
    feats = []
    for i, g in enumerate(geoms):
        gj = json.loads(json.dumps(mapping(g)))
        feats.append(
            {
                "type": "Feature",
                "properties": {"id": i, "capa": name},
                "geometry": gj,
            }
        )
    return {"type": "FeatureCollection", "name": name, "features": feats}


def _poly_paths(geom):
    polys = []
    if geom.geom_type == "Polygon":
        polys = [geom]
    elif geom.geom_type == "MultiPolygon":
        polys = list(geom.geoms)
    paths = []
    for poly in polys:
        verts = []
        codes = []
        ext = np.asarray(poly.exterior.coords)
        verts.append(ext)
        codes.append(
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(ext) - 2)
            + [MplPath.CLOSEPOLY]
        )
        for ring in poly.interiors:
            arr = np.asarray(ring.coords)
            verts.append(arr)
            codes.append(
                [MplPath.MOVETO]
                + [MplPath.LINETO] * (len(arr) - 2)
                + [MplPath.CLOSEPOLY]
            )
        paths.append(
            MplPath(np.concatenate(verts), np.concatenate(codes))
        )
    return paths


def _draw_geoms(ax, geoms, facecolor, edgecolor, lw, alpha_f, alpha_e=1.0, z=1):
    patches = []
    for g in geoms:
        for path in _poly_paths(g):
            patches.append(
                PathPatch(
                    path,
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    lw=lw,
                    alpha=alpha_f,
                    zorder=z,
                )
            )
    for p in patches:
        p.set_alpha(alpha_f)
        ax.add_patch(p)
        p.set_edgecolor(edgecolor)
        p.set_linewidth(lw)
        p.set_alpha(1.0 if alpha_e == 1 and alpha_f == 1 else alpha_f)


def _pack_leaflet() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    (VENDOR / "images").mkdir(parents=True, exist_ok=True)
    base = f"https://unpkg.com/leaflet@{LEAFLET_VER}/dist"
    files = {
        "leaflet.js": f"{base}/leaflet.js",
        "leaflet.css": f"{base}/leaflet.css",
        "images/marker-icon.png": f"{base}/images/marker-icon.png",
        "images/marker-icon-2x.png": f"{base}/images/marker-icon-2x.png",
        "images/marker-shadow.png": f"{base}/images/marker-shadow.png",
    }
    for rel, url in files.items():
        dest = VENDOR / rel
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    perim, crs_src, info = _read_geoms(LAYER_PERIM)
    print(
        f"perimetro n={len(perim)} src_crs={crs_src} "
        f"geom={info.get('geometry_type')}"
    )
    try:
        mun, _, _ = _read_geoms(LAYER_MUN)
    except Exception as exc:
        print(f"MunicipiosAMVA omitido: {exc}")
        mun = []

    fc = _to_wgs84_featurecollection(perim, LAYER_PERIM)
    geo_path = DATA / "perimetro_urbano_amva.geojson"
    geo_path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    west, south, east, north = BBOX_WGS84
    bounds = {
        "crs": "EPSG:4326",
        "south": south,
        "west": west,
        "north": north,
        "east": east,
        "bbox": [west, south, east, north],
        "imageOverlay": [[south, west], [north, east]],
        "layer": LAYER_PERIM,
        "src_crs": str(crs_src),
    }
    bounds_json = json.dumps(bounds, ensure_ascii=False, indent=2)
    (DATA / "basemap-bounds.json").write_text(bounds_json, encoding="utf-8")
    (DATA / "basemap_bounds.json").write_text(bounds_json, encoding="utf-8")

    lon_span = east - west
    lat_span = north - south
    width = 10.5
    height = width * (lat_span / lon_span) / max(math.cos(math.radians((south + north) / 2)), 0.9)
    fig, ax = plt.subplots(figsize=(width, height), dpi=140)
    fig.patch.set_facecolor("#143d1f")
    ax.set_facecolor("#143d1f")
    if mun:
        _draw_geoms(ax, mun, "#1B5E20", "#2E7D32", 0.45, 0.92, z=1)
    _draw_geoms(ax, perim, "#5BA83A", "#C8E6C0", 1.05, 0.42, z=2)
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(1 / math.cos(math.radians((south + north) / 2)))
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    png_path = DATA / "basemap_aburra.png"
    fig.savefig(png_path, facecolor=fig.get_facecolor(), pad_inches=0)
    plt.close(fig)

    _pack_leaflet()
    print(
        f"OK {geo_path.name}={geo_path.stat().st_size/1024:.0f}KB "
        f"{png_path.name}={png_path.stat().st_size/1024:.0f}KB "
        f"leaflet={ (VENDOR/'leaflet.js').stat().st_size/1024:.0f}KB"
    )


if __name__ == "__main__":
    main()
