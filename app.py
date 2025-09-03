import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# GitHub raw file URL (your Excel file in the repo)
RAW_FILE_URL = "https://raw.githubusercontent.com/chilli-23/scoreboard-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

# Load Excel data
def load_data():
    response = requests.get(RAW_FILE_URL)
    file_bytes = io.BytesIO(response.content)
    df = pd.read_excel(file_bytes, sheet_name="scorecard")

    # Standardize column names
    df = df.rename(columns={
        "CONDITION MONITORING SCORE": "SCORE",
        "DATE": "DATE",
        "AREA": "AREA",
        "SYSTEM": "SYSTEM",
        "EQUIPMENT DESCRIPTION": "EQUIPMENT"
    })

    # Clean types
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    return df

def main():
    st.title("📊 Condition Monitoring Scorecard Dashboard")

    # Load and clean data
    df = load_data()

    # 🔍 Debug section: highest scores
    st.subheader("Debug: Top 10 Highest Scores from Excel")
    st.write(df[["DATE", "EQUIPMENT", "SCORE"]].sort_values("SCORE", ascending=False).head(10))

    # Sidebar filters
    st.sidebar.header("Filters")
    area_list = df["AREA"].dropna().unique().tolist()
    area = st.sidebar.selectbox("Select Area", ["All"] + area_list)

    system_list = df["SYSTEM"].dropna().unique().tolist()
    system = st.sidebar.selectbox("Select System", ["All"] + system_list)

    equip_list = df["EQUIPMENT"].dropna().unique().tolist()
    equipment = st.sidebar.selectbox("Select Equipment", ["All"] + equip_list)

    # Apply filters
    df_filtered = df.copy()
    if area != "All":
        df_filtered = df_filtered[df_filtered["AREA"] == area]
    if system != "All":
        df_filtered = df_filtered[df_filtered["SYSTEM"] == system]
    if equipment != "All":
        df_filtered = df_filtered[df_filtered["EQUIPMENT"] == equipment]

    # Show filtered data
    st.subheader("Filtered Data")
    st.dataframe(df_filtered)

    # Score Trend Chart (scatter with markers)
    st.subheader("Trendline (Scores from Scorecard)")
    fig_trend = px.scatter(
        df_filtered,
        x="DATE",
        y="SCORE",
        color="EQUIPMENT",
        title="Condition Monitoring Score Trend",
        labels={"SCORE": "Condition Monitoring Score"},
    )
    fig_trend.update_traces(mode="lines+markers")
    st.plotly_chart(fig_trend, use_container_width=True)

if __name__ == "__main__":
    main()
