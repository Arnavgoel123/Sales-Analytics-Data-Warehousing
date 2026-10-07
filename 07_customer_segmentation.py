"""
Customer Segmentation via RFM Analysis + K-Means Clustering
Pulls transaction-level data from the warehouse, computes
Recency / Frequency / Monetary value per customer, then clusters
customers into segments.
"""

import pandas as pd
import psycopg2
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
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
N_CLUSTERS = 4  # number of customer segments to find

# ---------- Pull one row per sale, with customer + date info ----------
conn = psycopg2.connect(**DB_CONFIG)

query = """
    SELECT
        c.customer_id,
        c.customer_name,
        d.full_date,
        f.sale_id,
        f.total_amount
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.date_key = d.date_key;
"""
df = pd.read_sql(query, conn)
conn.close()

# ---------- Compute RFM per customer ----------
snapshot_date = df["full_date"].max() + pd.Timedelta(days=1)  # "today" = day after last sale

rfm = df.groupby("customer_id").agg(
    recency=("full_date", lambda x: (snapshot_date - x.max()).days),
    frequency=("sale_id", "nunique"),
    monetary=("total_amount", "sum"),
).reset_index()

# ---------- Scale features (K-Means is distance-based, needs comparable scales) ----------
features = rfm[["recency", "frequency", "monetary"]]
scaler = StandardScaler()
scaled_features = scaler.fit_transform(features)

# ---------- Fit K-Means ----------
kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
rfm["segment"] = kmeans.fit_predict(scaled_features)

# ---------- Label segments by their average characteristics ----------
segment_summary = rfm.groupby("segment").agg(
    avg_recency=("recency", "mean"),
    avg_frequency=("frequency", "mean"),
    avg_monetary=("monetary", "mean"),
    num_customers=("customer_id", "count"),
).reset_index().sort_values("avg_monetary", ascending=False)

print("Segment summary (sorted by avg spend):\n")
print(segment_summary.to_string(index=False))

# simple human-readable labels based on rank
labels = ["High-Value Loyal", "Steady Regulars", "At-Risk", "Low-Engagement"]
segment_summary["label"] = labels[:len(segment_summary)]
label_map = dict(zip(segment_summary["segment"], segment_summary["label"]))
rfm["segment_label"] = rfm["segment"].map(label_map)

print("\nCustomer counts per segment:")
print(rfm["segment_label"].value_counts())

# ---------- Save results ----------
rfm.to_csv("customer_segments.csv", index=False)
print("\nSaved full segment assignments to customer_segments.csv")

# ---------- Visualize: Frequency vs Monetary, colored by segment ----------
plt.figure(figsize=(8, 6))
for seg in rfm["segment"].unique():
    subset = rfm[rfm["segment"] == seg]
    plt.scatter(subset["frequency"], subset["monetary"],
                label=label_map[seg], alpha=0.6)
plt.xlabel("Frequency (number of orders)")
plt.ylabel("Monetary (total spend)")
plt.title("Customer Segments (RFM + K-Means)")
plt.legend()
plt.tight_layout()
plt.savefig("customer_segments.png")
print("Saved chart to customer_segments.png")
