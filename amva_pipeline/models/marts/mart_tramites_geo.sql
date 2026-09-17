-- Mart Gold a grano trámite (mapa + KPI de tiempo).
-- 1 fila = 1 trámite. Vista en AMVA_ENV.GOLD (trial: no copia tabla).
-- Tiempos: suma de horas/días de mart_tareas_sgc donde contar_dias_habiles = 'SI'.
-- Geo: columnas reales de DECIDE (municipio, latitud/longitud, visita).
-- No se inventan GPS. Si el punto no cae en el Valle de Aburrá, lat/lon quedan NULL
-- y el municipio sigue. Caja: lat 5.9–6.6, lon -75.7 a -75.3 (mismo criterio
-- del extracto AMVA; no es un centroide inventado).

with tareas as (
    select
        t.*,
        case
            when t.latitud between 5.9 and 6.6
                and t.longitud between -75.7 and -75.3
                then t.latitud
            when t.latitud_visita between 5.9 and 6.6
                and t.longitud_visita between -75.7 and -75.3
                then t.latitud_visita
        end as lat_valida,
        case
            when t.latitud between 5.9 and 6.6
                and t.longitud between -75.7 and -75.3
                then t.longitud
            when t.latitud_visita between 5.9 and 6.6
                and t.longitud_visita between -75.7 and -75.3
                then t.longitud_visita
        end as lon_valida,
        case
            when t.latitud between 5.9 and 6.6
                and t.longitud between -75.7 and -75.3
                then 'TRAMITE'
            when t.latitud_visita between 5.9 and 6.6
                and t.longitud_visita between -75.7 and -75.3
                then 'VISITA'
        end as origen_coordenada_tarea
    from {{ ref('mart_tareas_sgc') }} as t
),

kpis as (
    select
        tramite_id,
        count(*) as n_tareas,
        count(iff(contar_dias_habiles = 'SI', 1, null)) as n_tareas_sgc,
        round(sum(iff(contar_dias_habiles = 'SI', horas_habiles, null)), 4) as horas_habiles_sgc,
        round(sum(iff(contar_dias_habiles = 'SI', dias_habiles, null)), 4) as dias_habiles_sgc,
        round(sum(horas_habiles), 4) as horas_habiles_todas,
        min(fecha_inicio_tramite) as fecha_inicio_tramite,
        max(fecha_fin_tramite) as fecha_fin_tramite,
        max(fecha_decide) as fecha_decide
    from tareas
    group by tramite_id
),

ultima as (
    select
        tramite_id,
        municipio,
        codigo_municipio,
        clasificacion_permiso,
        tipo_tramite,
        estado_tramite,
        decision,
        estado_sgc,
        agrupacion_sgc,
        anio_inicio
    from tareas
    qualify row_number() over (
        partition by tramite_id
        order by tarea_orden desc, tarea_id desc
    ) = 1
),

geo as (
    select
        tramite_id,
        lat_valida as latitud,
        lon_valida as longitud,
        origen_coordenada_tarea as origen_coordenada
    from tareas
    where lat_valida is not null
      and lon_valida is not null
    qualify row_number() over (
        partition by tramite_id
        order by tarea_orden desc, tarea_id desc
    ) = 1
)

select
    k.tramite_id,
    u.municipio,
    u.codigo_municipio,
    u.clasificacion_permiso,
    u.tipo_tramite,
    u.estado_tramite,
    u.decision,
    u.estado_sgc,
    u.agrupacion_sgc,
    u.anio_inicio,
    k.fecha_inicio_tramite,
    k.fecha_fin_tramite,
    k.fecha_decide,
    k.n_tareas,
    k.n_tareas_sgc,
    k.horas_habiles_sgc,
    k.dias_habiles_sgc,
    k.horas_habiles_todas,
    g.latitud,
    g.longitud,
    g.origen_coordenada
from kpis as k
inner join ultima as u
    on u.tramite_id = k.tramite_id
left join geo as g
    on g.tramite_id = k.tramite_id
