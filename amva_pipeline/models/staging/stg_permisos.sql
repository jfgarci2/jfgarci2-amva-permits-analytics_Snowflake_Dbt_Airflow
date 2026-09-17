-- Staging DECIDE: 1 fila = 1 tarea. Sin lógica SGC / horas hábiles.
-- PII no entra: CODFUNCIONARIO, FUNCIONARIO, TERCERO se quitaron en Python.

with source as (
    select * from {{ source('bronze', 'permisos') }}
),

renamed as (
    select
        codtramite as tramite_id,
        codtarea as tarea_id,
        orden as tarea_orden,
        tarea as tarea_nombre,
        procesotramite as proceso,
        procesotarea as proceso_tarea,
        clasificacionpermiso as clasificacion_permiso,
        tipotramite as tipo_tramite,
        estadotramite as estado_tramite,
        estadotarea as estado_tarea,
        estadosgc as estado_sgc,
        agrupacion as agrupacion_sgc,
        grupo as grupo,
        decision as decision,
        municipio as municipio,
        cm as codigo_municipio,
        -- TRY_CAST(NUMBER AS TIMESTAMP) no compila. to_varchar cubre TIMESTAMP;
        -- serial Excel / epoch ns quedan como fallback en el macro.
        {{ cast_bronze_timestamp('iniciotramite') }} as fecha_inicio_tramite,
        {{ cast_bronze_timestamp('terminatramite') }} as fecha_fin_tramite,
        {{ cast_bronze_timestamp('iniciatarea') }} as fecha_inicia_tarea,
        {{ cast_bronze_timestamp('finalizatarea') }} as fecha_finaliza_tarea,
        {{ cast_bronze_timestamp('fechadecide') }} as fecha_decide,
        {{ cast_bronze_timestamp('fechaautoinicio') }} as fecha_auto_inicio,
        aniodecide as anio_decide,
        numerodecide as numero_decide,
        try_cast(longitud as float) as longitud,
        try_cast(latitud as float) as latitud,
        try_cast(longitudvisita as float) as longitud_visita,
        try_cast(latitudvisita as float) as latitud_visita
    from source
)

select * from renamed
