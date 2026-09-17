FROM apache/airflow:2.9.3-python3.11

USER airflow
RUN pip install --no-cache-dir \
    "dbt-snowflake>=1.9.0,<2.0.0" \
    pandas \
    pyarrow \
    pyyaml \
    openpyxl \
    "snowflake-connector-python[pandas]"
