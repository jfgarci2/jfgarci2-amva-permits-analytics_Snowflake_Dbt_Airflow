-- Calendario de días no laborables AMVA.
-- Grano: 1 fila = 1 fecha no laborable (festivo o fin de semana del extracto).
-- El SQL de HorasTotales / DiasHabiles debe ANTI-JOIN esta fecha.

with source as (
    select * from {{ source('bronze', 'dias_nolaborables') }}
),

renamed as (
    select
        id_nolaboral,
        cast(d_dia as date) as fecha_no_laborable,
        year as anio,
        month as mes,
        day as dia,
        weekday_num as dia_semana
    from source
)

select * from renamed
