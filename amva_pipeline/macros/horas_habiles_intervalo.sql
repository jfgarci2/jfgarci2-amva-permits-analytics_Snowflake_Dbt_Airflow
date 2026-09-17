{% macro horas_habiles_intervalo(
    ts_ini,
    ts_fin,
    d_ini,
    d_fin,
    h_ini,
    h_fin,
    es_habil_ini,
    es_habil_fin,
    n_festivos_lv_medio
) %}
{#
  HorasTotales (DAX / Python AMVA) entre dos timestamps:
    primer día parcial + días hábiles del medio × 10 h + último día parcial.
  Jornada 07:30–17:30. Noches = 0. Fin de semana = 0 (DAYOFWEEKISO 1–5).
  Festivos de entre semana se restan del tramo intermedio (no se restan
  sábados/domingos del calendario: ya salieron por ISO; no hay doble conteo).
#}
case
    when {{ ts_ini }} is null or {{ ts_fin }} is null then null
    when {{ ts_fin }} <= {{ ts_ini }} then 0
    when {{ d_ini }} = {{ d_fin }} then
        iff(
            {{ es_habil_ini }},
            {{ horas_parciales_laborales(d_ini, h_ini, h_fin) }},
            0
        )
    else
        iff(
            {{ es_habil_ini }},
            {{ horas_parciales_laborales(d_ini, h_ini, "time_from_parts(17, 30, 0)") }},
            0
        )
        + 10 * greatest(
            {{ n_lun_a_vie("dateadd('day', 1, " ~ d_ini ~ ")", "dateadd('day', -1, " ~ d_fin ~ ")") }}
            - coalesce({{ n_festivos_lv_medio }}, 0),
            0
        )
        + iff(
            {{ es_habil_fin }},
            {{ horas_parciales_laborales(d_fin, "time_from_parts(7, 30, 0)", h_fin) }},
            0
        )
end
{% endmacro %}
