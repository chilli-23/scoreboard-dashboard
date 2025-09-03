import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# ==============================
# Load Data
# ==============================
@st.cache_data
def load_data():
    url = "https://YOUR_FILE_URL_HERE"  # 🔹 Replace with your actual Excel file URL

    response = requests.get(url)
    if response.status_code != 200:
        st.error("❌ Could not fetch the Excel file. Please check the URL.")
        return None

    file_bytes = io.BytesIO(response.content)

    # Check available sheets
    xls = pd.ExcelFile(file_bytes)
    st.write("Available sheets:", xls.sheet_names)

    sheet_name = "scorecard"  # default expected sheet
    if sheet_name not in xls.sheet_names:
        st.warning(f"⚠️ Sheet '{sheet_name}' not found, using '{xls.sheet_names[0]}' instead.")
        sheet_name = xls.sheet_names[0]

    df = pd.read_excel(file_bytes, sheet_name=sheet_name)

    # Standardize column names
    df = df.rename(columns={
        "CONDITION MONITORING SCORE": "SCORE",
        "Date": "DATE",
        "Equipment": "EQUIPMENT"
    })

    # Convert types
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    return df

# ==============================
# Main App
# ==============================
def main():
    st.set_page_config(page_title="📊 Condition Monitoring Scorecard Dashboard", layout="wide")
    st.title("📊 Condition Monitoring Scorecard Dashboard")

    df = load_data()
    if df is None:
        return

    # Sidebar filters
    equipment_list = df["EQUIPMENT"].dropna().unique()
    selected_equipment = st.sidebar.selectbox("Select Equipment", equipment_list)

    # Filter data
    df_equip = df[df["EQUIPMENT"] == selected_equipment]

    # Show trendline (simple non-interactive)
    st.subheader(f"📈 Trendline for {selected_equipment}")
    fig_trend = px.line(
        df_equip,
        x="DATE",
        y="SCORE",
        title=f"Trend of {selected_equipment}",
        markers=True
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Date filter (Year + Month → Dates)
    df_equip["Year"] = df_equip["DATE"].dt.year
    df_equip["Month"] = df_equip["DATE"].dt.month

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Select Year", sorted(df_equip["Year"].dropna().unique()))
    with col2:
        month = st.selectbox("Select Month", sorted(df_equip["Month"].dropna().unique()))

    df_filtered = df_equip[(df_equip["Year"] == year) & (df_equip["Month"] == month)]

    available_dates = df_filtered["DATE"].dt.date.unique()
    selected_date = st.selectbox("Select Date", available_dates)

    df_selected = df_filtered[df_filtered["DATE"].dt.date == selected_date]

    # Show table
    st.subheader("📋 Scorecard Data")
    st.dataframe(df_selected)

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    main()
