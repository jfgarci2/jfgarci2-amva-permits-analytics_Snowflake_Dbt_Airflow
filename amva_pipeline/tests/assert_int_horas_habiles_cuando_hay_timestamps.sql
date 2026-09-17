-- Si hay INICIO y FIN, HorasTotales no puede quedar en blanco (0 sí es válido).
select *
from {{ ref('int_horas_habiles') }}
where fecha_inicia_tarea is not null
  and fecha_finaliza_tarea is not null
  and horas_habiles is null
