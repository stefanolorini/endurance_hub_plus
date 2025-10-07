# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./app.db")

# SQLite needs this; Postgres doesn't.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    # pool config only for non-sqlite
    **({} if DATABASE_URL.startswith("sqlite") else {"pool_size": 5, "max_overflow": 10})
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# >>> This is what main.py and models.py import <<<
Base = declarative_base()
