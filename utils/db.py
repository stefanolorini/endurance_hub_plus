import os
import streamlit as st
from sqlalchemy import create_engine

def _get(k, default=None):
    try:
        return st.secrets[k]
    except Exception:
        return os.getenv(k, default)

DATABASE_URL = _get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing. Add it to Streamlit Secrets (cloud) or .env (local).")

ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
