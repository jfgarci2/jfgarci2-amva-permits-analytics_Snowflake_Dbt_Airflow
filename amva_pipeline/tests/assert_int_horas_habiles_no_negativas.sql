-- Horas hábiles nunca negativas (NULL sí es válido si falta un timestamp).
select *
from {{ ref('int_horas_habiles') }}
where horas_habiles < 0
   or horas_habiles_hasta_hoy < 0
   or dias_habiles < 0
   or dias_habiles_hasta_hoy < 0
   or dias_habiles_mix < 0
