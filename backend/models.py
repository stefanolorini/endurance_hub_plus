from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    Integer, String, Float, Date, ForeignKey, Boolean,
    DateTime, Text, JSON, UniqueConstraint, func
)
from datetime import date, datetime
from typing import Optional


class Base(DeclarativeBase):
    pass


# --- Core tables ---
class Athlete(Base):
    __tablename__ = "athlete"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sex: Mapped[str] = mapped_column(String(10))
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    rhr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vo2max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ftp_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class TrainingBlock(Base):
    __tablename__ = "training_blocks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete.id"))
    block_length_weeks: Mapped[int] = mapped_column(Integer)
    recovery_weeks: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)


# --- Goals (targets + prompt) ---
class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete.id"))
    target_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_bodyfat_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_ftp_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    goal_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_constraints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeframe_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Activities (for TSS/fatigue) ---
class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete.id"))
    date: Mapped[date] = mapped_column(Date)
    sport: Mapped[str] = mapped_column(String(32))
    duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tss: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Body metrics (Apple Health import) ---
class BodyMetrics(Base):
    __tablename__ = "body_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete.id"))
    date: Mapped[date] = mapped_column(Date)

    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bodyfat_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vo2max_mlkgmin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resting_hr_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # FTP + provenance
    ftp_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ftp_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("athlete_id", "date", name="uix_body_metrics_day"),)
