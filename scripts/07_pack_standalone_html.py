"""Empaqueta el tablero en un HTML único (como el geoportal v3).

Se abre con doble clic (file://). No necesita Python ni Snowflake.
El mapa usa la foto local empaquetada (sin red). Satélite/Calles/Claro
son teselas Esri y sí necesitan internet.

Uso (raíz del repo):
  python scripts/07_pack_standalone_html.py

Salida:
  Geoportal_Permisos_Licencias_AMVA.html
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
OUT = ROOT / "Geoportal_Permisos_Licencias_AMVA.html"


def _b64_data_uri(path: Path, mime: str) -> str:
    raw = path.read_bytes()
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def _js_json(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.replace("</", "<\\/")


def main() -> None:
    html = (DASH / "index.html").read_text(encoding="utf-8")
    leaflet_css = (DASH / "vendor" / "leaflet" / "leaflet.css").read_text(encoding="utf-8")
    leaflet_js = (DASH / "vendor" / "leaflet" / "leaflet.js").read_text(encoding="utf-8")
    logo = _b64_data_uri(DASH / "assets" / "amva-logo.png", "image/png")
    foto = _b64_data_uri(DASH / "assets" / "satelite-aburra.jpg", "image/jpeg")

    html = html.replace(
        '<title>Geoportal de permisos y licencias ambientales — AMVA</title>',
        '<title>Geoportal de permisos y licencias ambientales — AMVA</title>\n'
        '<!-- Archivo único. Foto local funciona sin red. Satélite/Calles/Claro requieren internet. -->',
    )
    html = html.replace('href="assets/amva-logo.png"', f'href="{logo}"')
    html = html.replace('src="assets/amva-logo.png"', f'src="{logo}"')
    html = html.replace(
        '<link rel="stylesheet" href="vendor/leaflet/leaflet.css">',
        "<style>\n" + leaflet_css + "\n</style>",
    )
    html = html.replace(
        '<script src="vendor/leaflet/leaflet.js"></script>',
        "<script>\n" + leaflet_js + "\n</script>",
    )

    data_js = (
        "<script>\nwindow.__AMVA__ = {\n"
        "tramites: " + _js_json(DASH / "data" / "tramites.json") + ",\n"
        "tareas: " + _js_json(DASH / "data" / "tareas.json") + ",\n"
        "muni: " + _js_json(DASH / "data" / "capas" / "municipios_amva.geojson") + ",\n"
        "perim: " + _js_json(DASH / "data" / "capas" / "perimetro_urbano_amva.geojson") + ",\n"
        "red: " + _js_json(DASH / "data" / "capas" / "red_hidrica.geojson") + ",\n"
        "foto: " + json.dumps(foto) + "\n"
        "};\n</script>\n"
    )
    html = html.replace("<script>\n(function () {", data_js + "<script>\n(function () {")
    html = html.replace(
        """  Promise.all([
    fetch("data/tramites.json").then(r => r.json()),
    fetch("data/tareas.json").then(r => r.json()),
    fetch("data/capas/municipios_amva.geojson").then(r => r.json()),
    fetch("data/capas/perimetro_urbano_amva.geojson").then(r => r.json()),
    fetch("data/capas/red_hidrica.geojson").then(r => r.json())
  ]).then(([tramites, tareas, muni, perim, red]) => {""",
        """  Promise.resolve([
    window.__AMVA__.tramites,
    window.__AMVA__.tareas,
    window.__AMVA__.muni,
    window.__AMVA__.perim,
    window.__AMVA__.red
  ]).then(([tramites, tareas, muni, perim, red]) => {""",
    )

    OUT.write_text(html, encoding="utf-8")
    mb = OUT.stat().st_size / (1024 * 1024)
    print(f"OK {OUT.name} {mb:.2f} MB")
    print("Ábralo con doble clic. Foto local = sin red. Satélite/Calles necesitan internet.")
    print("Envío: Teams, OneDrive o WhatsApp (el correo suele rechazar ~20 MB).")
    if mb > 20:
        print("WARN el archivo supera 20 MB")


if __name__ == "__main__":
    main()
