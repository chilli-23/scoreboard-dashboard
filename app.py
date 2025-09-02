import os
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_plotly_events import plotly_events

st.set_page_config(page_title="Equipment Monitoring Dashboard", layout="wide")

# =============================
# Load Data (CSV / Upload / Sample)
# =============================
df = None
csv_file = "your_data.csv"

if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        st.warning("⚠️ No CSV found. Using sample data for now.")
        data = {
            "DATE": pd.date_range(start="2025-01-01", periods=10, freq="D"),
            "EQUIPMENT DESCRIPTION": ["Motor A", "Motor B"] * 5,
            "SCORE": [1, 0, 1, 1, 0, 1, 1, 0, 1, 1]
        }
        df = pd.DataFrame(data)

# =============================
# Data Preprocessing
# =============================
df["DATE"] = pd.to_datetime(df["DATE"])

# Sidebar filters
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start Date", df["DATE"].min().date())
end_date = st.sidebar.date_input("End Date", df["DATE"].max().date())

df_filtered_by_date = df[(df["DATE"] >= pd.to_datetime(start_date)) &
                         (df["DATE"] <= pd.to_datetime(end_date))]

equipments = df_filtered_by_date["EQUIPMENT DESCRIPTION"].unique()
selected_equip_name = st.sidebar.selectbox("Select Equipment", equipments)

# =============================
# Trendline Section
# =============================
st.subheader(f"Trendline for {selected_equip_name}")

# 1. Filter data for the selected equipment
trend_df_filtered = df_filtered_by_date[
    df_filtered_by_date["EQUIPMENT DESCRIPTION"] == selected_equip_name
].copy()

# 2. Group by DATE, get the minimum score per date
trend_df_filtered = trend_df_filtered.groupby('DATE')['SCORE'].min().reset_index()

# =============================
# TOP: Non-Clickable Trendline
# =============================
st.markdown("### 📊 Overall Trend (Non-Clickable)")
fig_trend_static = px.line(trend_df_filtered, x="DATE", y="SCORE", markers=True)
st.plotly_chart(fig_trend_static, use_container_width=True)

# =============================
# BOTTOM: Clickable Trendline
# =============================
st.markdown("### 🖱️ Drilldown Trend (Clickable)")
fig_trend_click = px.line(trend_df_filtered, x="DATE", y="SCORE", markers=True)
selected_points = plotly_events(
    fig_trend_click,
    click_event=True,
    key=f"trend_chart_click_{selected_equip_name}"
)

# If user clicks a point, show details
if selected_points:
    clicked_idx = selected_points[0]["pointIndex"]
    clicked_date = trend_df_filtered.iloc[clicked_idx]["DATE"]

    st.markdown(f"**You clicked on date: {clicked_date.date()}**")
    
    # Filter original data by clicked date (all equipment that day)
    clicked_day_data = df_filtered_by_date[df_filtered_by_date["DATE"] == clicked_date]
    st.dataframe(clicked_day_data)
