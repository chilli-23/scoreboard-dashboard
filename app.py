import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# ==============================
# Load Data
# ==============================
@st.cache_data
def load_data(file=None, url=None):
    df = None

    # Case 1: User uploads file
    if file is not None:
        df = pd.read_excel(file)

    # Case 2: Try URL if no file uploaded
    elif url is not None:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            file_bytes = io.BytesIO(response.content)

            # Get available sheets
            xls = pd.ExcelFile(file_bytes)
            sheet_name = "scorecard"
            if sheet_name not in xls.sheet_names:
                st.warning(f"⚠️ Sheet '{sheet_name}' not found, using '{xls.sheet_names[0]}' instead.")
                sheet_name = xls.sheet_names[0]

            df = pd.read_excel(file_bytes, sheet_name=sheet_name)
        except Exception as e:
            st.error(f"❌ Could not load data from URL: {e}")
            return None

    if df is None:
        return None

    # Standardize column names
    df = df.rename(columns={
        "CONDITION MONITORING SCORE": "SCORE",
        "Date": "DATE",
        "Equipment": "EQUIPMENT"
    })

    # Convert types
    if "SCORE" in df.columns:
        df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    return df

# ==============================
# Main App
# ==============================
def main():
    st.set_page_config(page_title="📊 Condition Monitoring Scorecard Dashboard", layout="wide")
    st.title("📊 Condition Monitoring Scorecard Dashboard")

    # Upload or URL option
    uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx"])
    url_input = st.sidebar.text_input("Or enter file URL", "https://raw.githubusercontent.com/chilli-23/scoreboard-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx")

    df = load_data(uploaded_file, url_input)
    if df is None:
        st.stop()

    # Sidebar filters
    equipment_list = df["EQUIPMENT"].dropna().unique()
    selected_equipment = st.sidebar.selectbox("Select Equipment", equipment_list)

    # Filter data
    df_equip = df[df["EQUIPMENT"] == selected_equipment]

    # Show trendline (simple)
    st.subheader(f"📈 Trendline for {selected_equipment}")
    fig_trend = px.line(
        df_equip,
        x="DATE",
        y="SCORE",
        title=f"Trend of {selected_equipment}",
        markers=True
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Year-Month filter
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
