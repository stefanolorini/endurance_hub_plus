import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
ENGINE = create_engine(os.getenv("DATABASE_URL"))

def df_to_sql(df: pd.DataFrame, table: str, if_exists="append"):
    df.to_sql(table, con=ENGINE, index=False, if_exists=if_exists)

def read_sql(query: str) -> pd.DataFrame:
    return pd.read_sql(query, ENGINE)
