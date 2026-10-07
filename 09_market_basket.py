"""
Market Basket Analysis on top of the Data Warehouse
Finds which products are frequently purchased together, using
the Apriori algorithm to generate association rules.
"""

import pandas as pd
import psycopg2
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

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
MIN_SUPPORT = 0.005    # item(set) must appear in at least 0.5% of orders
MIN_CONFIDENCE = 0.1   # rule must hold true at least 10% of the time

# ---------- Pull sub-categories per order (the "basket") ----------
# Using sub_category instead of individual product_name: with ~1850 unique
# products, pairwise product combos are too sparse to find patterns in.
# Sub-category (17 distinct values) gives meaningful, reportable patterns.
conn = psycopg2.connect(**DB_CONFIG)

query = """
    SELECT
        f.sale_id,
        p.sub_category
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key;
"""
df = pd.read_sql(query, conn)
conn.close()

# ---------- Build one basket (list of sub-categories) per order ----------
# drop_duplicates: if an order has 2 "Binders" items, we only want it counted once
df = df.drop_duplicates()
baskets = df.groupby("sale_id")["sub_category"].apply(list).tolist()

# keep only multi-item orders -- single-item orders can't reveal co-purchase patterns
baskets = [b for b in baskets if len(b) > 1]
print(f"Analyzing {len(baskets)} multi-item orders out of {df['sale_id'].nunique()} total orders.")

# ---------- One-hot encode: rows = orders, columns = products, True/False ----------
te = TransactionEncoder()
te_array = te.fit(baskets).transform(baskets)
basket_df = pd.DataFrame(te_array, columns=te.columns_)

# ---------- Find frequent itemsets ----------
frequent_itemsets = apriori(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
print(f"\nFound {len(frequent_itemsets)} frequent itemsets.")

if len(frequent_itemsets) == 0:
    print("No frequent itemsets found -- try lowering MIN_SUPPORT.")
else:
    # ---------- Generate association rules ----------
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=MIN_CONFIDENCE)
    rules = rules.sort_values("lift", ascending=False)

    # ---------- Show top rules, readable format ----------
    display_rules = rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(15)
    display_rules["antecedents"] = display_rules["antecedents"].apply(lambda x: ", ".join(list(x)))
    display_rules["consequents"] = display_rules["consequents"].apply(lambda x: ", ".join(list(x)))

    print("\nTop association rules (by lift):\n")
    print(display_rules.to_string(index=False))

    display_rules.to_csv("market_basket_rules.csv", index=False)
    print("\nSaved full rules to market_basket_rules.csv")
