-- Planned vs actual hours/day
create or replace view v_plan_vs_actual as
select
  p.date,
  p.duration_hr as planned_hours,
  coalesce(a.hours,0) as actual_hours,
  coalesce(a.hours,0) - p.duration_hr as delta_hours
from plan p
left join (
  select date_trunc('day', ts)::date as date, sum(moving_time_sec)/3600.0 as hours
  from activities
  group by 1
) a on a.date = p.date;

-- 14-day weight delta
create or replace view v_weight_trend as
select d1.date, d1.weight_kg, d14.weight_kg as weight_kg_14d_ago,
       (d1.weight_kg - d14.weight_kg) as delta_14d
from daily_metrics d1
left join lateral (
  select dm.weight_kg from daily_metrics dm
  where dm.date = d1.date - interval '14 days'
  limit 1
) d14 on true;
