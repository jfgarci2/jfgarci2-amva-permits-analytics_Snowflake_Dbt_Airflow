# Extractos AMVA — carpeta `raw`

Ruta absoluta (copiar para scripts):

```text
D:\PROJECTS-ANALITYICS ENGINEER\AMVA PROJECTS\amva-environmental-permits- DBT- SNOWFLAKE-AIRFLOW\Bases de datos AMVA\raw
```

Esta carpeta es la **fuente de verdad en disco** del extracto AMVA (sistema operativo **DECIDE**). No nos conectamos a Oracle. Los `.xlsx` están **gitignored** (PII + archivos de ~45–50 MB). Este README **sí** se versiona.

## `DIAS_NOLABORABLES.xlsx` — obligatorio (no opcional)

Calendario de **días no laborables / festivos AMVA**. **Todas** las métricas de tiempo del SGC dependen de este archivo:

| Concepto (DAX original) | Qué hace |
|-------------------------|----------|
| `HorasTotales` | Horas hábiles entre dos instantes. |
| `DiasHabiles` | Días hábiles (no calendario corrido). |
| Jornada | 7:30–17:30. |
| Exclusiones | Sábado, domingo **y** las fechas de este Excel. |

El SQL dbt de horas/días hábiles **debe hacer join / anti-join** a Bronze `dias_nolaborables` (source stub: `amva_pipeline/models/staging/sources.yml`). Sin este calendario, `DiasHabiles` y `HorasTotales` están mal.

No es un seed opcional “por si acaso”. Es el **motor** del cálculo de tiempo. Un seed dbt puede copiarlo más adelante; hoy el Excel vive aquí.

### Esquema (inspección Python / openpyxl — no se versiona el xlsx)

Hoja única: `DIAS_NOLABORABLES`. **1180 filas**, 6 columnas, 0 nulos.

| Columna | Tipo | Rol |
|---------|------|-----|
| `ID_NOLABORAL` | entero | Clave del extracto (min 1, max 1201). |
| `D_DIA` | fecha | **Fecha a excluir.** Rango **2016-01-01 → 2025-11-30**. 1180 fechas únicas. |
| `YEAR` / `MONTH` / `DAY` | entero | Partes de `D_DIA`. Años 2016–2025. |
| `WEEKDAY_NUM` | entero | 6 = sábado, 7 = domingo (ISO-like). 1–5 = festivo en lunes–viernes. El archivo **incluye fines de semana y festivos de entre semana**. |

## Extractos DECIDE (gitignored)

Fuente de verdad en Bronze: `QRY_PERMISOSAMBIENTALES_DECIDE_31082026.xlsx` (~48.1 MB). Ingesta completa (`scripts/03_load_permisos_sample.py`, `SAMPLE_ROWS=None`): **216414** filas en `AMVA_ENV.BRONZE.PERMISOS`. El archivo `_27052026.xlsx` queda como histórico, no se carga.

- `QRY_PERMISOSAMBIENTALES_DECIDE_27052026.xlsx` (~44.3 MB)
- `QRY_PERMISOSAMBIENTALES_DECIDE_31082026.xlsx` (~48.1 MB)

Contienen PII (`CODFUNCIONARIO`, `FUNCIONARIO`, `TERCERO`, etc.). Antes de Bronze: anonimizar (Ley 1581). El script de carga los elimina y convierte fechas Excel a `TIMESTAMP_NTZ` (no serial NUMBER).

## Qué sí / qué no va a Git

| Archivo | Git |
|---------|-----|
| Este `README.md` | Sí |
| `DIAS_NOLABORABLES.xlsx` | **No** |
| `QRY_PERMISOSAMBIENTALES_DECIDE_*.xlsx` | **No** |

Captura de esta carpeta: [`docs/screenshots/13-raw-dias-nolaborables.png`](../../docs/screenshots/13-raw-dias-nolaborables.png).
