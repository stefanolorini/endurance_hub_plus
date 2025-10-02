import streamlit as st
import pandas as pd

def safe_query(run_query_fn, empty_ok=False, error_message="Problem loading data."):
    try:
        df = run_query_fn()
        if isinstance(df, pd.DataFrame):
            if df.empty and not empty_ok:
                st.info("No data yet. Upload a plan or run an ingest.")
            return df
        return df
    except Exception as e:
        st.error(f"{error_message}\n\n**Details:** {e}")
        st.stop()

def require_secret(key: str, friendly: str = ""):
    if key in st.secrets and st.secrets[key]:
        return st.secrets[key]
    st.error(f"Missing `{key}`. Add it in **Settings → Secrets**. {friendly}")
    st.stop()

def kpi_card(label, value, help_text=None):
    c1, c2 = st.columns([1,2])
    with c1: st.markdown(f"### {label}")
    with c2:
        st.markdown(f"## {value}")
        if help_text: st.caption(help_text)
