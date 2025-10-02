create table if not exists activities (
  id bigserial primary key,
  athlete_id uuid,
  source text,
  activity_id text unique,
  ts timestamptz,
  type text,
  name text,
  distance_km numeric,
  moving_time_sec integer,
  elapsed_time_sec integer,
  avg_power numeric,
  max_power numeric,
  avg_hr numeric,
  max_hr numeric,
  elevation_gain_m numeric,
  calories numeric,
  tss numeric,
  ifactor numeric,
  ftp numeric
);

create table if not exists daily_metrics (
  id bigserial primary key,
  athlete_id uuid,
  date date,
  rhr numeric,
  hrv_ms numeric,
  sleep_duration_min integer,
  sleep_score numeric,
  body_battery integer,
  vo2max numeric,
  weight_kg numeric,
  body_fat_pct numeric,
  pulse_wave_velocity_ms numeric
);

create table if not exists plan (
  id bigserial primary key,
  athlete_id uuid,
  date date,
  session_type text,
  description text,
  duration_hr numeric,
  target_kj numeric,
  target_kcal numeric,
  nutrition_day text,
  kcal integer,
  protein_g integer,
  carbs_g integer,
  fat_g integer,
  supplements text
);

create table if not exists weather (
  id bigserial primary key,
  date date,
  lat numeric,
  lon numeric,
  temp_c numeric,
  wind_kph numeric,
  precip_prob numeric
);
