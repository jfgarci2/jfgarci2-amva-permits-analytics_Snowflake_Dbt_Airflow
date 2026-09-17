# Capturas Snowsight (AMVA)

Carpeta de evidencia visual para el informe del proyecto de permisos ambientales (dbt + Snowflake + Airflow).

**No versionar ni pegar contrase?as** en este directorio ni en el informe. Las capturas pueden mostrar usuario, cuenta y URL; eso no incluye la contrase?a.

## Warehouses de la cuenta trial

En esta cuenta **no existe `COMPUTE_WH`**. El trial muestra:

- `AMVA_WH` ? Standard, **X-Small**, estado **Suspended**. Warehouse del proyecto (Auto-resume y Auto-suspend). Tras crearlo qued? **Started**; el usuario indic? **Suspend inmediatamente**.
- `SNOWFLAKE_LEARNING_WH` ? Standard, **X-Small**, estado **Suspended**. Warehouse de aprendizaje de Snowflake.
- `SYSTEM$STREAMLIT_NOTEBOOK_WH` ? Standard, **X-Small**, Suspended. Warehouse interno del sistema (**no usar** para dbt ni para el proyecto).

Los tres warehouses est?n **Suspended** y **X-Small** salvo cuando un SQL reanuda `AMVA_WH`. **No usar** `SYSTEM$STREAMLIT_NOTEBOOK_WH`.

## Workspaces (Snowsight)

Snowsight ya no abre el worksheet cl?sico: la UI nueva es **Workspaces** (`Projects` ? `Workspaces`). En **Welcome to Workspaces** hay que abrir un **SQL file**. **No** abrir Notebook, Streamlit App ni dbt Project en Snowflake; dbt se ejecuta en local / Airflow contra Snowflake, no como proyecto nativo de Snowsight.

El DDL de `AMVA_ENV` se corri? en el archivo **`Untitled.sql`**, warehouse **`AMVA_WH` (X-Small)**. El dropdown de rol de la UI sigue en **ACCOUNTADMIN** (el SQL incluye `USE ROLE SYSADMIN`). El `SELECT` de identificador devolvi? **`NVSMAZV-BE58602`**. `SELECT CURRENT_USER(), CURRENT_ROLE()` devolvi? usuario **`jfgarci206`** y rol de sesi?n **`ACCOUNTADMIN`** (si solo se corre el ?ltimo SELECT, `USE ROLE SYSADMIN` no aplica).

## Archivos

- `01-snowsight-home-trial-400.png` ? **principal para el informe.** Home de Snowsight tras el login. Visible: JOSE GARCIA, rol ACCOUNTADMIN, cr?dito de prueba **$400 of $400 remaining**, trial de **30 days**, URL `app.snowflake.com/nvsmazv/be58602/`. **No pulsar Upgrade** (pasar a pago).
- `00-snowflake-signup-company.png` ? formulario de registro (opcional; menos ?til para el informe).
- `02-warehouses-learning-wh-suspended.png` ? lista Compute ? Warehouses. Confirma que **no hay `COMPUTE_WH`**: solo `SNOWFLAKE_LEARNING_WH` (XS, Suspended) y `SYSTEM$STREAMLIT_NOTEBOOK_WH` (no usar).
- `03-new-warehouse-dialog.png` ? di?logo **New warehouse** al crear `AMVA_WH` (nombre pendiente de escribir; Type Standard Gen2, Size X-Small, Auto-resume y Auto-suspend 5 min).
- `04-new-warehouse-amva-wh-settings.png` ? di?logo **New warehouse** con `AMVA_WH`: Standard Gen1, X-Small, auto-suspend 1 min, 1 cr?dito/hora, query acceleration off.
- `05-amva-wh-created-started.png` ? lista Compute ? Warehouses tras crear **`AMVA_WH`**: Standard, **X-Small**, estado **Started** (1/1 clusters). Tambi?n aparecen `SNOWFLAKE_LEARNING_WH` (Suspended) y `SYSTEM$STREAMLIT_NOTEBOOK_WH` (**no usar**). El usuario indic? **Suspend inmediatamente** para no consumir cr?ditos del trial.
- `06-amva-wh-resumed-15s.png` ? `AMVA_WH` **STANDARD_GEN_1**, estado **Running** (Running 0), **Resumed 15 seconds ago**. El usuario indic? **Suspend** desde el men? de la fila.
- `07-amva-wh-suspended.png` ? lista Compute ? Warehouses con **`AMVA_WH`**, `SNOWFLAKE_LEARNING_WH` y `SYSTEM$STREAMLIT_NOTEBOOK_WH` todos **Suspended**, **X-Small**. Listo para el DDL de **`AMVA_ENV`**.
- `08-workspaces-welcome.png` ? **Welcome to Workspaces** (`Projects` ? `Workspaces`). Tiles: **SQL file**, Notebook, dbt Project, Streamlit App. El usuario abri? **SQL file**. **No** abrir dbt Project nativo de Snowflake.
- `09-sql-role-warehouse-picker.png` ? archivo **`Untitled.sql`**. Picker de sesi?n: rol UI **ACCOUNTADMIN**, warehouse **`AMVA_WH` (X-Small)** (tambi?n aparecen `SNOWFLAKE_LEARNING_WH` y `SYSTEM$STREAMLIT_NOTEBOOK_WH`; no usarlos).
- `10-sql-create-amva-env.png` ? SQL pegado: `USE ROLE SYSADMIN;` + `CREATE DATABASE AMVA_ENV` + schemas **BRONZE / SILVER / GOLD** + `SELECT` del account identifier. Rol del dropdown sigue **ACCOUNTADMIN**.
- `11-account-identifier-nvsmazv-be58602.png` ? resultado **SUCCESS** (1 row, 99 ms). Columna `ACCOUNT_IDENTIFIER` = **`NVSMAZV-BE58602`**. Sin contrase?as.
- `12-current-user-jfgarci206.png` ? `Untitled.sql`. Resultado **SUCCESS** (1 row, 56 ms): `USUARIO` = **`jfgarci206`**, `ROL` = **`ACCOUNTADMIN`**. Dropdown UI **ACCOUNTADMIN**, warehouse **`AMVA_WH` (X-Small)**. Login name para `profiles.yml`. Sin contrase?as.
- `dashboard-run8.png` ? tablero HTML local (`http://localhost:8000`). KPI RUN 8: 4.025 tr?mites, 1.182 GPS, 19 municipios, 111,02 d?as h?biles. Sin contrase?as.
