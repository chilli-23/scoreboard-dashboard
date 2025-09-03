import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import requests
import io

# -------------------------------
# Load Data
# -------------------------------
RAW_FILE_URL = "https://raw.githubusercontent.com/chilli-23/scoreboard-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

@st.cache_data
def load_data():
    response = requests.get(RAW_FILE_URL)
    return pd.read_excel(io.BytesIO(response.content), sheet_name="Scorecard", header=1)

df = load_data()

# -------------------------------
# Normalize column names
# -------------------------------
df.columns = df.columns.str.strip().str.upper()

st.title("📊 Condition Monitoring Dashboard")
st.write("✅ Loaded columns:", df.columns.tolist())

# -------------------------------
# Check required columns
# -------------------------------
required_cols = ["DATE", "SCORE", "EQUIPMENT DESCRIPTION"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Missing required columns in Excel: {missing}")
    st.stop()

# Ensure date column is datetime
df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

# -------------------------------
# Map status function
# -------------------------------
def map_status(score):
    if score == 1:
        return "🔴 BAD"
    elif score == 2:
        return "🟡 FAIR"
    elif score == 3:
        return "🟢 GOOD"
    return "⚪ UNKNOWN"

df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

# -------------------------------
# Sidebar filters
# -------------------------------
st.sidebar.header("Filters")
equipments = df["EQUIPMENT DESCRIPTION"].dropna().unique()
selected_equip = st.sidebar.selectbox("Choose Equipment", sorted(equipments))

date_min, date_max = df["DATE"].min(), df["DATE"].max()
selected_date = st.sidebar.slider(
    "Select Date Range",
    min_value=date_min,
    max_value=date_max,
    value=(date_min, date_max)
)

df_filtered = df[(df["DATE"] >= selected_date[0]) & (df["DATE"] <= selected_date[1])]

# -------------------------------
# Static Trend Line
# -------------------------------
st.subheader("Static Trend Line")
fig_static = px.line(
    df_filtered,
    x="DATE",
    y="SCORE",
    color="EQUIPMENT DESCRIPTION",
    markers=True,
    title="Condition Monitoring Trend (Static)"
)
st.plotly_chart(fig_static, use_container_width=True)

# -------------------------------
# Interactive Trend Line
# -------------------------------
st.subheader("Interactive Trend Line (click legend to toggle)")
fig_interactive = px.line(
    df_filtered,
    x="DATE",
    y="SCORE",
    color="EQUIPMENT DESCRIPTION",
    markers=True,
    title="Condition Monitoring Trend (Interactive)"
)
fig_interactive.update_layout(
    legend=dict(itemclick="toggle", itemdoubleclick="toggleothers"),
    yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1)
)
st.plotly_chart(fig_interactive, use_container_width=True)

# -------------------------------
# Trendline for selected equipment
# -------------------------------
st.subheader(f"Performance Trend for {selected_equip}")

df_equip = df_filtered[df_filtered["EQUIPMENT DESCRIPTION"] == selected_equip].copy()

if not df_equip.empty:
    idx = df_equip.groupby("DATE")["SCORE"].idxmin()
    aggregated_df = df_equip.loc[idx].reset_index(drop=True)
    aggregated_df["EQUIP_STATUS"] = aggregated_df["SCORE"].apply(map_status)

    fig_trend = px.line(
        aggregated_df,
        x="DATE",
        y="SCORE",
        markers=True,
        title=f"Trendline for {selected_equip}"
    )
    fig_trend.update_xaxes(tickformat="%d/%m/%y", fixedrange=True)
    fig_trend.update_layout(
        yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1, fixedrange=True)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    selected_points = plotly_events(fig_trend, click_event=True, key=f"trend_chart_{selected_equip}")

    if selected_points:
        clicked_date = pd.to_datetime(selected_points[0]["x"]).normalize()
        selected_row = aggregated_df[aggregated_df["DATE"].dt.normalize() == clicked_date].iloc[0]

        st.subheader(f"Details for {selected_equip} on {selected_row['DATE'].strftime('%d-%m-%Y')}")
        st.markdown(f"**Score:** {selected_row['SCORE']}")
        st.markdown(f"**Status:** {selected_row['EQUIP_STATUS']}")
        st.markdown(f"**Finding:** {selected_row.get('FINDING', 'N/A')}")
        st.markdown(f"**Action Plan:** {selected_row.get('ACTION PLAN', 'N/A')}")
    else:
        st.info("Click a point on the trend chart to see details for that specific date.")
else:
    st.warning(f"No trend data available for {selected_equip} in the selected date range.")
