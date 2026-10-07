"""
SCD Type 2 handler for dim_customer.

Run this on subsequent data loads (not the initial load).
For each incoming customer record:
  - If customer is new -> insert as a fresh row (is_current = TRUE)
  - If customer exists but tracked attributes changed ->
        close out the old row (end_date = today, is_current = FALSE)
        insert a new row with updated values (is_current = TRUE)
  - If customer exists and nothing changed -> do nothing
"""

import pandas as pd
import psycopg2
from datetime import date

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
CSV_PATH = "Sample - Superstore.csv"  # new/updated customer records to process

# columns we track for changes (if any of these differ, it's a new version)
TRACKED_COLS = ["Customer Name", "Segment", "City", "State"]

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
today = date.today()

incoming = pd.read_csv(CSV_PATH)
incoming = incoming.drop_duplicates(subset=["Customer ID"])

for _, row in incoming.iterrows():
    cid = row["Customer ID"]

    # fetch the current active row for this customer, if any
    cur.execute(
        """SELECT customer_name, segment, city, state
           FROM dim_customer
           WHERE customer_id = %s AND is_current = TRUE""",
        (cid,),
    )
    existing = cur.fetchone()

    new_values = (row["Customer Name"], row["Segment"], row["City"], row["State"])

    if existing is None:
        # brand new customer -> simple insert
        cur.execute(
            """INSERT INTO dim_customer
               (customer_id, customer_name, segment, city, state,
                start_date, end_date, is_current)
               VALUES (%s, %s, %s, %s, %s, %s, '9999-12-31', TRUE)""",
            (cid, *new_values, today),
        )

    elif existing != new_values:
        # existing customer, but something changed -> expire old row, insert new
        cur.execute(
            """UPDATE dim_customer
               SET end_date = %s, is_current = FALSE
               WHERE customer_id = %s AND is_current = TRUE""",
            (today, cid),
        )
        cur.execute(
            """INSERT INTO dim_customer
               (customer_id, customer_name, segment, city, state,
                start_date, end_date, is_current)
               VALUES (%s, %s, %s, %s, %s, %s, '9999-12-31', TRUE)""",
            (cid, *new_values, today),
        )

    # else: existing == new_values -> no change, skip

conn.commit()
cur.close()
conn.close()
print("SCD Type 2 update complete.")
