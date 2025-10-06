INSERT INTO athlete (id, name, sex, age, height_cm, weight_kg, rhr, vo2max, ftp_w)
VALUES (1,'Stef','M',35,176,74,50,57,300)
ON CONFLICT DO NOTHING;

INSERT INTO training_blocks (athlete_id, block_length_weeks, recovery_weeks, start_date)
VALUES (1, 3, 1, CURRENT_DATE)
ON CONFLICT DO NOTHING;
