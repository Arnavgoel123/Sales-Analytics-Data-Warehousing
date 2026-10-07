"""
Sales Forecasting on top of the Data Warehouse
Pulls monthly revenue straight from fact_sales + dim_date,
then forecasts the next N months using Prophet.
"""

import pandas as pd
import psycopg2
from prophet import Prophet
import matplotlib.pyplot as plt

import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT"),
}

FORECAST_MONTHS = 6  # how far ahead to predict

# ---------- Pull aggregated monthly revenue from the warehouse ----------
conn = psycopg2.connect(**DB_CONFIG)

query = """
    SELECT
        MAKE_DATE(d.year, d.month, 1) AS month_start,
        SUM(f.total_amount)           AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month
    ORDER BY month_start;
"""
df = pd.read_sql(query, conn)
conn.close()

# ---------- Prophet requires columns named exactly 'ds' and 'y' ----------
df_prophet = df.rename(columns={"month_start": "ds", "revenue": "y"})

# ---------- Fit the model ----------
model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
model.fit(df_prophet)

# ---------- Build future dataframe and predict ----------
future = model.make_future_dataframe(periods=FORECAST_MONTHS, freq="MS")  # MS = month start
forecast = model.predict(future)

# ---------- Show the forecasted values (last N rows = the new predictions) ----------
result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(FORECAST_MONTHS)
result.columns = ["Month", "Predicted Revenue", "Lower Bound", "Upper Bound"]
print(result.to_string(index=False))

# ---------- Plot actual vs forecast ----------
fig = model.plot(forecast)
plt.title("Monthly Sales Revenue Forecast")
plt.xlabel("Month")
plt.ylabel("Revenue")
plt.tight_layout()
plt.savefig("sales_forecast.png")
print("\nSaved chart to sales_forecast.png")

# ---------- Optional: plot seasonality/trend components ----------
fig2 = model.plot_components(forecast)
plt.savefig("sales_forecast_components.png")
print("Saved components chart to sales_forecast_components.png")
