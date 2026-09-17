{% macro n_lun_a_vie(fecha_ini, fecha_fin) %}
{#
  Cuenta lunes–viernes INCLUSIVOS entre dos fechas.
  No usa DATEDIFF('week'): depende de WEEK_START de la sesión.
  DAYOFWEEKISO es estable (lunes=1 … domingo=7).
  Los festivos NO se restan aquí: eso va en el modelo (anti-join).
#}
iff(
    {{ fecha_ini }} is null
    or {{ fecha_fin }} is null
    or {{ fecha_fin }} < {{ fecha_ini }},
    0,
    floor((datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1) / 7) * 5
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 0
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 0, 7) + 1 between 1 and 5,
        1, 0
    )
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 1
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 1, 7) + 1 between 1 and 5,
        1, 0
    )
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 2
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 2, 7) + 1 between 1 and 5,
        1, 0
    )
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 3
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 3, 7) + 1 between 1 and 5,
        1, 0
    )
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 4
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 4, 7) + 1 between 1 and 5,
        1, 0
    )
    + iff(
        mod(datediff('day', {{ fecha_ini }}, {{ fecha_fin }}) + 1, 7) > 5
        and mod(dayofweekiso({{ fecha_ini }}) - 1 + 5, 7) + 1 between 1 and 5,
        1, 0
    )
)
{% endmacro %}
