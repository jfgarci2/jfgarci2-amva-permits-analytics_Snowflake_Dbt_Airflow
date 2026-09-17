# Tablero — permisos ambientales AMVA

Geoportal al estilo `Geoportal_Permisos_Licencias_AMVA_v3.html`: mapa a pantalla completa, consulta a la izquierda, convenciones a la derecha. Capas locales desde `Shapefiles` (municipios, perímetro urbano, red hídrica) y trámites desde JSON (Gold). El navegador no consulta Snowflake. Las bases Calles / Satélite / Claro usan teselas Esri (internet). Sin PII.

## Cómo abrirlo

No abra `index.html` con doble clic (`file://`).

Desde la raíz del repo:

```powershell
python -m http.server 8000 --directory dashboard
```

Luego **http://localhost:8000**

## Cómo enviarlo

Comprima la carpeta `dashboard/` completa:

- `index.html`
- `assets/` (logo, fondo AMVA, `satelite-aburra.jpg`)
- `data/` (JSON, GeoJSON, `basemap-bounds.json`)
- `vendor/` (Leaflet local)

Quien reciba el zip debe servir esa carpeta con `python -m http.server`. Las capas vectoriales van en `data/capas/` (salida de `scripts/05_shapefiles_to_geojson.py`).

## Regenerar datos

```powershell
python scripts/04_export_dashboard_json.py
python scripts/05_shapefiles_to_geojson.py
```

`04` usa `profiles.yml` (usuario `AMVA_DBT`) y escribe `data/tramites.json` + `data/tareas.json`.
`05` convierte los shapefiles de `Shapefiles/` a `data/capas/`.
