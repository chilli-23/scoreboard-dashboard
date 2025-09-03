import streamlit as st
import pandas as pd
import plotly.express as px
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

# Make sure Date column is datetime
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

st.title("📊 Condition Monitoring Dashboard")

# -------------------------------
# Static Trend Line
# -------------------------------
st.subheader("Static Trend Line")

fig_static = px.line(
    df,
    x="Date",
    y="Score",
    color="Equipment",
    markers=True,
    title="Condition Monitoring Trend (Static)"
)
st.plotly_chart(fig_static, use_container_width=True)

# -------------------------------
# Interactive Trend Line
# -------------------------------
st.subheader("Interactive Trend Line (click legend to toggle)")

fig_interactive = px.line(
    df,
    x="Date",
    y="Score",
    color="Equipment",
    markers=True,
    title="Condition Monitoring Trend (Interactive)"
)

# Enable legend toggle
fig_interactive.update_layout(
    legend=dict(
        itemclick="toggle",
        itemdoubleclick="toggleothers"
    )
)

st.plotly_chart(fig_interactive, use_container_width=True)

st.info("💡 Tip: Click legend items to hide/show lines. Double-click to isolate one.")
