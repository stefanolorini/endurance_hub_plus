import pandas as pd
from utils.weather import get_daily_weather
from utils.db import df_to_sql

def main():
    data = get_daily_weather()
    if not data:
        print("No weather data fetched.")
        return
    df = pd.DataFrame(data)
    df_to_sql(df, "weather")
    print(f"Upserted {len(df)} weather rows (duplicates will be ignored if configured).")

if __name__ == "__main__":
    main()
