# Endurance Hub + (Plan • Data • Adaptation)

A pragmatic dashboard that unifies your **plan** (training + nutrition + supplements) and your **real-world data**
(Strava/Garmin, Apple Health), and suggests **adaptations** based on readiness, training load, weather, and goals.

## Quick start
1. `pip install -r requirements.txt`
2. Create `.env` from `.env.example` (set `DATABASE_URL`, Strava creds, etc.)
3. Create tables: run `schema.sql` in your DB (Supabase or local Postgres).
4. `streamlit run app.py`
5. Upload your plan CSV in **Admin Uploads** page (same columns as your workbook).
6. Import data:
   - **Strava** activities via `utils/strava_client.py` (token refresh included).
   - **Apple Health**: on iPhone → Health → Profile → Export All Health Data → upload the **zip** in Admin.
   - **Garmin** daily: optional, via `garminconnect` library (unofficial).

## Adaptations
- Readiness: HRV ↓ > 15% vs 7‑day median **and** RHR ↑ > 5 bpm, or sleep < 7h → reduce intensity.
- Load: TSB < −10 → reduce; TSB > +5 → okay to progress.
- Weather: precip > 70% or wind > 30 kph → swap to indoor or shift sessions.
- Weight trend: loss > 0.7 kg/week → increase kcal; < 0.2 kg/week (while cutting) → reduce kcal modestly.

Use `pages/04_Adaptation_Rules.py` to view daily suggestions.
