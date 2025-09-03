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

# -------------------------------
# Normalize column names
# -------------------------------
df.columns = df.columns.str.strip().str.lower()

st.title("📊 Condition Monitoring Dashboard")
st.write("✅ Loaded columns:", df.columns.tolist())

# -------------------------------
# Check required columns
# -------------------------------
required_cols = ["date", "score", "equipment"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Missing required columns in Excel: {missing}")
    st.stop()

# Ensure date column is datetime
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# -------------------------------
# Static Trend Line
# -------------------------------
st.subheader("Static Trend Line")

fig_static = px.line(
    df,
    x="date",
    y="score",
    color="equipment",
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
    x="date",
    y="score",
    color="equipment",
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
