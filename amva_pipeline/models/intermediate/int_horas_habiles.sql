-- Horas habiles AMVA (replica SQL de HorasTotales DAX / script Python).
-- Grano: 1 fila = 1 tarea (igual que stg_permisos). Vista Silver, sin PII.
--
-- Formula:
--   Si falta INICIO o FIN -> NULL.
--   Si FIN <= INICIO -> 0.
--   Si mismo dia -> interseccion del intervalo con 07:30-17:30 (0 si no es habil).
--   Si varios dias -> horas del primer dia (desde la hora de inicio hasta 17:30)
--     + 10 h * (lunes-viernes estrictamente entre medio - festivos de lun-vie)
--     + horas del ultimo dia (desde 07:30 hasta la hora de fin).
-- Jornada = 10 horas (07:30-17:30). Noches no cuentan.
-- Dia habil = DAYOFWEEKISO 1-5 Y la fecha NO esta en stg_dias_nolaborables.
-- El Excel trae sabados/domingos Y festivos de entre semana, pero le faltan
-- algunos fines de semana: por eso el filtro ISO es obligatorio.
-- No hay doble resta: n_lun_a_vie ya ignora sab/dom; del calendario solo
-- restamos festivos de lunes a viernes en el tramo intermedio.
-- Calendario del extracto: 2016-01-01 a 2025-11-30. Despues de esa fecha
-- seguimos quitando fines de semana; festivos de lun-vie ya no estan en el Excel.

with festivos as (
    select fecha_no_laborable
    from {{ ref('stg_dias_nolaborables') }}
),

-- Solo lun-vie del calendario. Los sab/dom del Excel no se restan otra vez.
festivos_lun_vie as (
    select fecha_no_laborable
    from festivos
    where dayofweekiso(fecha_no_laborable) between 1 and 5
),

tareas as (
    select
        p.*,
        row_number() over (
            order by p.tramite_id, p.tarea_orden, p.tarea_id, p.fecha_inicia_tarea
        ) as tarea_rn,
        p.fecha_inicia_tarea as ts_ini,
        p.fecha_finaliza_tarea as ts_fin,
        p.fecha_inicia_tarea::date as d_ini,
        p.fecha_finaliza_tarea::date as d_fin,
        p.fecha_inicia_tarea::time as h_ini,
        p.fecha_finaliza_tarea::time as h_fin,
        least(
            coalesce(
                p.fecha_finaliza_tarea,
                current_timestamp()::timestamp_ntz
            ),
            current_timestamp()::timestamp_ntz
        ) as ts_fin_hoy
    from {{ ref('stg_permisos') }} as p
),

tareas_fechas as (
    select
        t.*,
        t.ts_fin_hoy::date as d_fin_hoy,
        t.ts_fin_hoy::time as h_fin_hoy
    from tareas as t
),

-- Join + group: Snowflake no permite el COUNT correlacionado aqui.
festivos_medio as (
    select
        t.tarea_rn,
        count(f.fecha_no_laborable) as n_festivos_lv_medio
    from tareas_fechas as t
    left join festivos_lun_vie as f
        on t.d_ini is not null
       and t.d_fin is not null
       and f.fecha_no_laborable > t.d_ini
       and f.fecha_no_laborable < t.d_fin
    group by t.tarea_rn
),

festivos_medio_hoy as (
    select
        t.tarea_rn,
        count(f.fecha_no_laborable) as n_festivos_lv_medio_hoy
    from tareas_fechas as t
    left join festivos_lun_vie as f
        on t.d_ini is not null
       and t.d_fin_hoy is not null
       and f.fecha_no_laborable > t.d_ini
       and f.fecha_no_laborable < t.d_fin_hoy
    group by t.tarea_rn
),

con_calendario as (
    select
        t.*,
        (
            dayofweekiso(t.d_ini) between 1 and 5
            and f_ini.fecha_no_laborable is null
        ) as es_habil_ini,
        (
            dayofweekiso(t.d_fin) between 1 and 5
            and f_fin.fecha_no_laborable is null
        ) as es_habil_fin,
        (
            dayofweekiso(t.d_fin_hoy) between 1 and 5
            and f_hoy.fecha_no_laborable is null
        ) as es_habil_fin_hoy,
        m.n_festivos_lv_medio,
        h.n_festivos_lv_medio_hoy
    from tareas_fechas as t
    left join festivos_medio as m
        on m.tarea_rn = t.tarea_rn
    left join festivos_medio_hoy as h
        on h.tarea_rn = t.tarea_rn
    left join festivos as f_ini
        on f_ini.fecha_no_laborable = t.d_ini
    left join festivos as f_fin
        on f_fin.fecha_no_laborable = t.d_fin
    left join festivos as f_hoy
        on f_hoy.fecha_no_laborable = t.d_fin_hoy
),

calculado as (
    select
        c.* exclude (
            tarea_rn,
            ts_ini,
            ts_fin,
            d_ini,
            d_fin,
            h_ini,
            h_fin,
            ts_fin_hoy,
            d_fin_hoy,
            h_fin_hoy,
            es_habil_ini,
            es_habil_fin,
            es_habil_fin_hoy,
            n_festivos_lv_medio,
            n_festivos_lv_medio_hoy
        ),
        round(
            {{ horas_habiles_intervalo(
                'c.ts_ini',
                'c.ts_fin',
                'c.d_ini',
                'c.d_fin',
                'c.h_ini',
                'c.h_fin',
                'c.es_habil_ini',
                'c.es_habil_fin',
                'c.n_festivos_lv_medio'
            ) }},
            4
        ) as horas_habiles,
        round(
            {{ horas_habiles_intervalo(
                'c.ts_ini',
                'c.ts_fin_hoy',
                'c.d_ini',
                'c.d_fin_hoy',
                'c.h_ini',
                'c.h_fin_hoy',
                'c.es_habil_ini',
                'c.es_habil_fin_hoy',
                'c.n_festivos_lv_medio_hoy'
            ) }},
            4
        ) as horas_habiles_hasta_hoy
    from con_calendario as c
)

select
    *,
    iff(
        horas_habiles is null,
        null,
        round(horas_habiles / 10, 4)
    ) as dias_habiles,
    iff(
        horas_habiles_hasta_hoy is null,
        null,
        round(horas_habiles_hasta_hoy / 10, 4)
    ) as dias_habiles_hasta_hoy,
    coalesce(
        iff(horas_habiles is null, null, round(horas_habiles / 10, 4)),
        iff(
            horas_habiles_hasta_hoy is null,
            null,
            round(horas_habiles_hasta_hoy / 10, 4)
        )
    ) as dias_habiles_mix
from calculado
