{% macro horas_parciales_laborales(fecha, hora_desde, hora_hasta) %}
{#
  Horas de un SOLO día recortadas a la jornada AMVA 07:30–17:30.
  El caller debe haber comprobado que el día es hábil (lun–vie y no festivo).
  Si el intervalo recortado queda vacío (antes de 07:30, después de 17:30),
  devuelve 0.
#}
iff(
    {{ fecha }} is null
    or {{ hora_desde }} is null
    or {{ hora_hasta }} is null
    or greatest({{ hora_desde }}, time_from_parts(7, 30, 0))
        >= least({{ hora_hasta }}, time_from_parts(17, 30, 0)),
    0,
    timediff(
        'second',
        timestamp_ntz_from_parts(
            {{ fecha }},
            greatest({{ hora_desde }}, time_from_parts(7, 30, 0))
        ),
        timestamp_ntz_from_parts(
            {{ fecha }},
            least({{ hora_hasta }}, time_from_parts(17, 30, 0))
        )
    ) / 3600.0
)
{% endmacro %}
