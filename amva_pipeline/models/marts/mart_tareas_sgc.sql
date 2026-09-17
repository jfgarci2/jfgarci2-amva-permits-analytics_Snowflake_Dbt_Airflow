-- Mart delgado de tiempos por tarea (Gold).
-- Grano: 1 fila = 1 tarea. Vista en AMVA_ENV.GOLD (trial: no copia tabla).
-- Horas/días salen de int_horas_habiles (SQL Snowflake, no Python).
-- Grupo de trabajo SGC_Modificado_v7 se calcula en scripts/sgc_modificado.py
-- (TAREA + ESTADOSGC + Firmas por funcionario en RAM). No se usa la columna
-- GRUPO de DECIDE (esa es año-tipo de permiso). FUNCIONARIO no queda en Gold.
-- contar_dias_habiles = ContarDiasHabiles_Unificado_V2 (DAX):
--   NO si no hay Auto de Inicio ni Actuación Jurídica, o si ORDEN < ese inicio;
--   SI si el trámite no tiene fecha_decide (abierto) y la tarea ya está en el conteo;
--   SI si está decidido y la tarea inició y finalizó en o antes de fecha_decide.

with tareas as (
    select *
    from {{ ref('int_horas_habiles') }}
),

norm as (
    select
        t.*,
        translate(
            upper(trim(coalesce(t.tarea_nombre, ''))),
            'ÁÉÍÓÚÜÑáéíóúüñ',
            'AEIOUUNAEIOUUN'
        ) as tarea_nombre_norm
    from tareas as t
),

con_inicio as (
    select
        n.*,
        min(
            iff(n.tarea_nombre_norm = 'AUTO DE INICIO', n.tarea_orden, null)
        ) over (partition by n.tramite_id) as orden_auto_inicio,
        min(
            iff(n.tarea_nombre_norm = 'ACTUACION JURIDICA', n.tarea_orden, null)
        ) over (partition by n.tramite_id) as orden_actuacion_juridica
    from norm as n
)

select
    c.* exclude (tarea_nombre_norm, orden_auto_inicio, orden_actuacion_juridica),
    coalesce(c.orden_auto_inicio, c.orden_actuacion_juridica) as orden_inicio_conteo,
    case
        when coalesce(c.orden_auto_inicio, c.orden_actuacion_juridica) is null
            then 'NO'
        when c.tarea_orden < coalesce(c.orden_auto_inicio, c.orden_actuacion_juridica)
            then 'NO'
        when c.fecha_decide is null
            then 'SI'
        when c.fecha_inicia_tarea is not null
            and c.fecha_finaliza_tarea is not null
            and c.fecha_inicia_tarea::date <= c.fecha_decide::date
            and c.fecha_finaliza_tarea::date <= c.fecha_decide::date
            then 'SI'
        else 'NO'
    end as contar_dias_habiles,
    extract(year from c.fecha_inicio_tramite) as anio_inicio,
    extract(month from c.fecha_inicio_tramite) as mes_inicio
from con_inicio as c
