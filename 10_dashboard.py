"""
Sales Analytics Data Warehouse — Streamlit Dashboard
Run with: streamlit run 10_dashboard.py
"""

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

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

st.set_page_config(page_title="Sales Analytics Warehouse", layout="wide")


@st.cache_data(ttl=300)
def run_query(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# ---------- HEADER ----------
st.title("📊 Sales Analytics Data Warehouse")
st.caption("Star-schema warehouse · SCD Type 2 · ETL pipeline · ML forecasting")

# ---------- TOP-LEVEL KPIs ----------
kpi_query = """
    SELECT
        SUM(total_amount) AS total_revenue,
        SUM(profit)        AS total_profit,
        COUNT(DISTINCT sale_id) AS total_orders,
        COUNT(DISTINCT customer_key) AS total_customers
    FROM fact_sales;
"""
kpis = run_query(kpi_query).iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
col2.metric("Total Profit", f"${kpis['total_profit']:,.0f}")
col3.metric("Total Orders", f"{kpis['total_orders']:,}")
col4.metric("Customer Records", f"{kpis['total_customers']:,}")

st.divider()

# ---------- TABS ----------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Revenue Overview", "Products & Categories", "Customer Segments", "Forecast"]
)

# ===================== TAB 1: REVENUE OVERVIEW =====================
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Revenue by Region")
        region_df = run_query("""
            SELECT r.region_name, SUM(f.total_amount) AS revenue
            FROM fact_sales f
            JOIN dim_region r ON f.region_key = r.region_key
            GROUP BY r.region_name
            ORDER BY revenue DESC;
        """)
        fig = px.bar(region_df, x="region_name", y="revenue", color="region_name")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Monthly Revenue Trend")
        monthly_df = run_query("""
            SELECT d.year, d.month, SUM(f.total_amount) AS revenue
            FROM fact_sales f
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY d.year, d.month
            ORDER BY d.year, d.month;
        """)
        monthly_df["period"] = monthly_df["year"].astype(str) + "-" + monthly_df["month"].astype(str).str.zfill(2)
        fig = px.line(monthly_df, x="period", y="revenue", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Weekend vs Weekday Sales")
    weekend_df = run_query("""
        SELECT d.is_weekend, COUNT(*) AS num_orders, SUM(f.total_amount) AS revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.is_weekend;
    """)
    weekend_df["day_type"] = weekend_df["is_weekend"].map({True: "Weekend", False: "Weekday"})
    c3, c4 = st.columns(2)
    c3.plotly_chart(px.pie(weekend_df, names="day_type", values="revenue", title="Revenue Share"), use_container_width=True)
    c4.dataframe(weekend_df[["day_type", "num_orders", "revenue"]], use_container_width=True)

# ===================== TAB 2: PRODUCTS & CATEGORIES =====================
with tab2:
    st.subheader("Top 10 Products by Revenue")
    top_products = run_query("""
        SELECT p.product_name, p.category, SUM(f.total_amount) AS revenue, SUM(f.quantity) AS units_sold
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_name, p.category
        ORDER BY revenue DESC
        LIMIT 10;
    """)
    fig = px.bar(top_products, x="revenue", y="product_name", color="category", orientation="h")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Category")
    cat_df = run_query("""
        SELECT p.category, SUM(f.total_amount) AS revenue, SUM(f.profit) AS profit
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY revenue DESC;
    """)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(cat_df, names="category", values="revenue", title="Revenue Share"), use_container_width=True)
    c2.plotly_chart(px.bar(cat_df, x="category", y="profit", title="Profit by Category"), use_container_width=True)

# ===================== TAB 3: CUSTOMER SEGMENTS =====================
with tab3:
    st.subheader("Customer Segments (RFM + K-Means)")
    try:
        seg_df = pd.read_csv("customer_segments.csv")
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.scatter(
                seg_df, x="frequency", y="monetary", color="segment_label",
                hover_data=["customer_id", "recency"],
                title="Customer Segments: Frequency vs Monetary",
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.write("**Segment sizes**")
            st.dataframe(seg_df["segment_label"].value_counts().reset_index(), use_container_width=True)
        st.write("**Full segment table**")
        st.dataframe(seg_df, use_container_width=True)
    except FileNotFoundError:
        st.warning("Run `python 07_customer_segmentation.py` first to generate customer_segments.csv.")

    st.subheader("Customer Segment Performance (by stated segment field)")
    segment_perf = run_query("""
        SELECT c.segment, COUNT(DISTINCT c.customer_id) AS num_customers,
               SUM(f.total_amount) AS total_revenue, AVG(f.total_amount) AS avg_order_value
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        GROUP BY c.segment
        ORDER BY total_revenue DESC;
    """)
    st.dataframe(segment_perf, use_container_width=True)

# ===================== TAB 4: FORECAST =====================
with tab4:
    st.subheader("Sales Forecast")
    import os
    if os.path.exists("sales_forecast.png"):
        st.image("sales_forecast.png", caption="Monthly Revenue Forecast (Prophet)")
    else:
        st.warning("Run `python 05_forecast.py` first to generate the forecast chart.")

    if os.path.exists("sales_forecast_components.png"):
        st.image("sales_forecast_components.png", caption="Trend & Seasonality Components")

    st.subheader("Market Basket Rules")
    try:
        rules_df = pd.read_csv("market_basket_rules.csv")
        st.dataframe(rules_df, use_container_width=True)
    except FileNotFoundError:
        st.warning("Run `python 09_market_basket.py` first to generate market_basket_rules.csv.")

st.divider()
st.caption("Built on PostgreSQL star-schema warehouse · ETL via pandas/psycopg2 · ML via Prophet, scikit-learn, mlxtend")
