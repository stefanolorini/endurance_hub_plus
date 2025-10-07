

from sqlalchemy import Column, Integer, String, Float, Date, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from db import Base  # IMPORTANT: use the shared Base from db.py

import models                   
from db import Base  


class Athlete(Base):
    __tablename__ = "athlete"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    sex = Column(String)
    age = Column(Integer)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    rhr = Column(Float)
    vo2max = Column(Float)
    ftp_w = Column(Float)

class TrainingBlock(Base):
    __tablename__ = "training_block"
    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athlete.id"))
    start_date = Column(Date)
    block_length_weeks = Column(Integer)
    recovery_weeks = Column(Integer)

class BodyMetrics(Base):
    __tablename__ = "body_metrics"
    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athlete.id"))
    date = Column(Date, index=True)
    weight_kg = Column(Float)
    bodyfat_pct = Column(Float)
    vo2max_mlkgmin = Column(Float)
    resting_hr_bpm = Column(Float)
    ftp_w = Column(Float)
    ftp_source = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class Activity(Base):
    __tablename__ = "activity"
    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athlete.id"))
    date = Column(Date, index=True)
    sport = Column(String)
    duration_min = Column(Integer)
    tss = Column(Integer)

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athlete.id"))
    target_weight_kg = Column(Float)
    target_bodyfat_pct = Column(Float)
    target_ftp_w = Column(Float)
    goal_prompt = Column(Text)
    parsed_constraints = Column(Text)
    timeframe_weeks = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
