"""Build-time only: stitch Esri World Imagery tiles into a local JPEG.

The HTML never calls this URL. Re-run only if dashboard/assets/satelite-aburra.jpg is missing.
"""
from __future__ import annotations

import io
import json
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

WEST, SOUTH, EAST, NORTH = -75.665796, 6.068293, -75.319622, 6.450710
ZOOM = 14
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "assets" / "satelite-aburra.jpg"
BOUNDS = ROOT / "dashboard" / "data" / "basemap-bounds.json"
UA = {"User-Agent": "AMVA-dashboard-pack/1.0"}
TILE = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)


def deg2num(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = n * ((lon + 180.0) / 360.0)
    ytile = n * (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0
    return xtile, ytile


def tile_nw(x: int, y: int, zoom: int) -> tuple[float, float]:
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def fetch_tile(z: int, x: int, y: int) -> tuple[int, int, bytes]:
    url = TILE.format(z=z, y=y, x=x)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return x, y, r.read()


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    BOUNDS.parent.mkdir(parents=True, exist_ok=True)

    x0f, y_north = deg2num(NORTH, WEST, ZOOM)
    x1f, y_south = deg2num(SOUTH, EAST, ZOOM)
    x0, x1 = int(math.floor(x0f)), int(math.floor(x1f))
    y0, y1 = int(math.floor(y_north)), int(math.floor(y_south))
    xs = list(range(x0, x1 + 1))
    ys = list(range(y0, y1 + 1))
    jobs = [(x, y) for y in ys for x in xs]
    print(f"zoom={ZOOM} tiles={len(jobs)} grid={len(xs)}x{len(ys)}")

    mosaic = Image.new("RGB", (len(xs) * 256, len(ys) * 256), (18, 28, 16))
    ok = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(fetch_tile, ZOOM, x, y) for x, y in jobs]
        for fut in as_completed(futs):
            x, y, raw = fut.result()
            if raw[:2] != b"\xff\xd8" and raw[:8] != b"\x89PNG\r\n\x1a\n":
                continue
            tile = Image.open(io.BytesIO(raw)).convert("RGB")
            mosaic.paste(tile, ((x - x0) * 256, (y - y0) * 256))
            ok += 1
    print(f"ok_tiles={ok}/{len(jobs)} mosaic={mosaic.size}")

    nw_lat, nw_lon = tile_nw(x0, y0, ZOOM)
    se_lat, se_lon = tile_nw(x1 + 1, y1 + 1, ZOOM)
    lon_span = se_lon - nw_lon
    lat_span = nw_lat - se_lat
    left = int(round((WEST - nw_lon) / lon_span * mosaic.width))
    right = int(round((EAST - nw_lon) / lon_span * mosaic.width))
    top = int(round((nw_lat - NORTH) / lat_span * mosaic.height))
    bottom = int(round((nw_lat - SOUTH) / lat_span * mosaic.height))
    left, top = max(0, left), max(0, top)
    right, bottom = min(mosaic.width, right), min(mosaic.height, bottom)
    crop = mosaic.crop((left, top, right, bottom))
    print(f"crop={crop.size}")

    quality = 82
    crop.save(OUT, "JPEG", quality=quality, optimize=True)
    size_mb = OUT.stat().st_size / (1024 * 1024)
    if size_mb > 12.5:
        crop.save(OUT, "JPEG", quality=74, optimize=True)
        size_mb = OUT.stat().st_size / (1024 * 1024)
    elif size_mb < 4.5:
        crop.save(OUT, "JPEG", quality=90, optimize=True)
        size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"saved {OUT} {size_mb:.2f} MB")

    payload = {
        "crs": "EPSG:4326",
        "south": SOUTH,
        "west": WEST,
        "north": NORTH,
        "east": EAST,
        "imageOverlay": [[SOUTH, WEST], [NORTH, EAST]],
        "source": "Esri World Imagery tiles stitched at build time (not requested by the HTML)",
        "zoom": ZOOM,
    }
    BOUNDS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("bounds written")


if __name__ == "__main__":
    main()
