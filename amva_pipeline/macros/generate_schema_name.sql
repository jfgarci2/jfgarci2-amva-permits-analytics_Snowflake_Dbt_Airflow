{% macro generate_schema_name(custom_schema_name, node) -%}
{#
  Por defecto dbt concatenaría SILVER_GOLD.
  Con este macro, +schema: GOLD escribe en AMVA_ENV.GOLD.
#}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
