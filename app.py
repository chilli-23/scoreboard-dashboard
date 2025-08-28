import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# Helper functions (for styling and status mapping)
# =========================

def map_status(score):
    """Converts a numeric score (1, 2, 3) to a text status."""
    if score == 1:
        return "RED"
    elif score == 2:
        return "AMBER"
    elif score == 3:
        return "GREEN"
    return "UNKNOWN"

def color_score(val):
    """Applies background color to a cell based on its numeric score."""
    if val == 1:
        return "background-color: red; color: white;"
    elif val == 2:
        return "background-color: yellow; color: black;"
    elif val == 3:
        return "background-color: green; color: white;"
    return ""

def color_status(val):
    """Applies background color to a cell based on its text status."""
    if val == "RED":
        return "background-color: red; color: white;"
    elif val == "AMBER":
        return "background-color: orange; color: black;"
    elif val == "GREEN":
        return "background-color: green; color: white;"
    return ""

# =========================
# Main Streamlit App
# =========================
def main():
    st.set_page_config(layout="wide")
    st.title("📊 Condition Monitoring Dashboard")

    uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
    if not uploaded_file:
        st.info("Please upload a file to continue.")
        return

    # Load data from the "Scorecard" sheet
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Scorecard", header=1)
    except Exception as e:
        st.error(f"Error reading the 'Scorecard' sheet in the file: {e}")
        return

    # Clean up column names
    df.columns = [col.strip().upper() for col in df.columns]
    
    # Define the target column name, accounting for potential line breaks
    score_col_name = "CONDITION MONITORING \nSCORE"
    if score_col_name not in df.columns:
        score_col_name = "CONDITION MONITORING SCORE" # Fallback to single line
        if score_col_name not in df.columns:
            st.error("Error: A column named 'CONDITION MONITORING SCORE' was not found in your file.")
            return
        
    df = df.rename(columns={score_col_name: "SCORE"})
    
    # Convert score to a number, coercing errors to 'Not a Number' (NaN)
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors='coerce')

    # Parse date and drop rows with invalid dates or scores
    df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
    df.dropna(subset=['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE'], inplace=True)
    
    # Convert score to integer
    df["SCORE"] = df["SCORE"].astype(int)

    # Create the text-based status column for the pie charts
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    # --- FILTERS ---
    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]

    if df.empty:
        st.warning("No data available for the selected date range.")
        return

    # --- HIERARCHICAL AGGREGATION (using the score from Excel) ---
    system_scores = df.groupby(["AREA", "SYSTEM"])["SCORE"].min().reset_index()
    area_scores = system_scores.groupby("AREA")["SCORE"].min().reset_index()

    # ======================
    # 📊 BAR CHARTS
    # ======================
    st.subheader("AREA Score Distribution")
    fig_area = px.bar(
        area_scores, x="AREA", y="SCORE",
        color=area_scores["SCORE"].astype(str),
        text="SCORE",
        color_discrete_map={"3": "green", "2": "yellow", "1": "red"},
        title="Lowest Score per AREA"
    )
    fig_area.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1))
    st.plotly_chart(fig_area, use_container_width=True)

    st.subheader("SYSTEM Score Distribution")
    fig_system = px.bar(
        system_scores, x="SYSTEM", y="SCORE",
        color=system_scores["SCORE"].astype(str),
        text="SCORE",
        color_discrete_map={"3": "green", "2": "yellow", "1": "red"},
        title="Lowest Score per SYSTEM"
    )
    fig_system.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1), xaxis=dict(tickangle=-45))
    st.plotly_chart(fig_system, use_container_width=True)

    # ======================
    # 🥧 PIE CHARTS
    # ======================
    st.subheader("Equipment Status Distribution per AREA")
    area_dist = df.groupby(["AREA", "EQUIP_STATUS"])["EQUIPMENT DESCRIPTION"].count().reset_index(name="COUNT")
    areas = sorted(area_dist["AREA"].unique())

    cols_per_row = 3
    for i in range(0, len(areas), cols_per_row):
        cols = st.columns
