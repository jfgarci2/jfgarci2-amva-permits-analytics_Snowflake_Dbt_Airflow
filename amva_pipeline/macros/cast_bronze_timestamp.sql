{% macro cast_bronze_timestamp(column_name) %}
{#
  TRY_CAST(NUMBER AS TIMESTAMP) no compila. Siempre pasamos por VARCHAR.
  1) timestamp / texto ISO
  2) serial Excel (días desde 1899-12-30) → unix seconds como NUMBER
  3) epoch nanosegundos (write_pandas sin logical type)
#}
coalesce(
    try_cast(to_varchar({{ column_name }}) as timestamp_ntz),
    iff(
        try_to_double(to_varchar({{ column_name }})) between 1 and 100000,
        to_timestamp_ntz(
            ((try_to_double(to_varchar({{ column_name }})) - 25569) * 86400)::number
        ),
        iff(
            try_to_double(to_varchar({{ column_name }})) > 1e15,
            to_timestamp_ntz(
                (try_to_double(to_varchar({{ column_name }})) / 1e9)::number
            ),
            null
        )
    )
)
{% endmacro %}
