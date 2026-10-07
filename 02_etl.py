

"""
ETL script: Superstore CSV -> Sales Analytics Data Warehouse
Order: dim_product, dim_customer, dim_region  ->  fact_sales
(dimensions must load first so fact_sales foreign keys resolve)
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ---------- CONFIG ----------
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
CSV_PATH = "Sample - Superstore.csv"  # update to your actual file path

# ---------- EXTRACT ----------
df = pd.read_csv(CSV_PATH, encoding="latin1")

# ---------- TRANSFORM ----------
df["Order Date"] = pd.to_datetime(df["Order Date"])
df["date_key"] = df["Order Date"].dt.strftime("%Y%m%d").astype(int)

# drop rows with missing essentials (basic cleaning)
df = df.dropna(subset=["Order ID", "Customer ID", "Product ID", "Sales", "Quantity"])
df = df.drop_duplicates()

# unique dimension slices
products = df[["Product ID", "Product Name", "Category", "Sub-Category"]].drop_duplicates(subset=["Product ID"])
customers = df[["Customer ID", "Customer Name", "Segment", "City", "State"]].drop_duplicates(subset=["Customer ID"])
regions = df[["Region"]].drop_duplicates()
regions["Country"] = "United States"  # Superstore is US-only

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# ---------- LOAD: dim_product ----------
execute_values(
    cur,
    """INSERT INTO dim_product (product_id, product_name, category, sub_category)
       VALUES %s""",
    products.values.tolist(),
)

# ---------- LOAD: dim_customer ----------
execute_values(
    cur,
    """INSERT INTO dim_customer (customer_id, customer_name, segment, city, state)
       VALUES %s""",
    customers.values.tolist(),
)

# ---------- LOAD: dim_region ----------
execute_values(
    cur,
    """INSERT INTO dim_region (region_name, country)
       VALUES %s""",
    regions.values.tolist(),
)

conn.commit()

# ---------- Build lookup maps (natural key -> surrogate key) ----------
cur.execute("SELECT product_key, product_id FROM dim_product")
product_map = {pid: pkey for pkey, pid in cur.fetchall()}

cur.execute("SELECT customer_key, customer_id FROM dim_customer WHERE is_current = TRUE")
customer_map = {cid: ckey for ckey, cid in cur.fetchall()}

cur.execute("SELECT region_key, region_name FROM dim_region")
region_map = {rname: rkey for rkey, rname in cur.fetchall()}

# ---------- Build fact rows ----------
fact_rows = []
for _, row in df.iterrows():
    fact_rows.append((
        row["Order ID"],
        int(row["date_key"]),
        product_map[row["Product ID"]],
        customer_map[row["Customer ID"]],
        region_map[row["Region"]],
        int(row["Quantity"]),
        float(row["Discount"]),
        float(row["Sales"]),
        float(row.get("Profit", 0) or 0),
    ))

# ---------- LOAD: fact_sales ----------
execute_values(
    cur,
    """INSERT INTO fact_sales
       (sale_id, date_key, product_key, customer_key, region_key,
        quantity, discount, total_amount, profit)
       VALUES %s""",
    fact_rows,
)

conn.commit()
cur.close()
conn.close()

print(f"Loaded {len(products)} products, {len(customers)} customers, "
      f"{len(regions)} regions, {len(fact_rows)} sales.")
