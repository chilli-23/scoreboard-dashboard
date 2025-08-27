import streamlit as st
import pandas as pd
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="Equipment Condition Dashboard", layout="wide")
st.title("📊 Equipment Condition Dashboard")

# --- Constants ---
# Define required columns to ensure the uploaded file is correct.
REQUIRED_COLS = {
    "AREA",
    "SYSTEM",
    "EQUIPMENT DESCRIPTION",
    "DATE",
    "CONDITION MONITORING SCORE",
    "VIBRATION",
    "OIL ANALYSIS",
    "TEMPERATURE",
    "OTHER INSPECTION",
}

# --- Helper Functions ---

@st.cache_data # Use Streamlit's cache to avoid reloading data on every interaction.
def load_scorecard(uploaded_file) -> pd.DataFrame:
    """
    Read the 'Scorecard' sheet from the uploaded Excel file.
    It intelligently tries several possible header rows to find the correct one.
    """
    # Create a copy in memory to avoid issues with Streamlit's file buffer
    file_buffer = BytesIO(uploaded_file.getvalue())
    
    tried_headers = []
    # Common header row indices in Excel (0-based for pandas)
    for header_row in [1, 0, 2, 3, 4]: 
        try:
            df = pd.read_excel(file_buffer, sheet_name="Scorecard", header=header_row)
            # Standardize column names for consistency
            df.columns = df.columns.str.strip().str.upper()
            
            # If all required columns are present, we've found the right header.
            if REQUIRED_COLS.issubset(set(df.columns)):
                return df
            tried_headers.append((header_row, df.columns.tolist()))
        except Exception as e:
            tried_headers.append((header_row, f"Error: {e}"))
            
    # If the loop finishes without returning, the file is invalid.
    st.error(
        "Could not find all required columns in the 'Scorecard' sheet.\n"
        f"Required columns: {', '.join(sorted(REQUIRED_COLS))}"
    )
    with st.expander("See Debugging Details"):
        st.write("Attempted header rows and the columns found:")
        st.json(tried_headers)
    st.stop() # Stop the script if the file is not valid.


def coerce_score(value):
    """
    Converts various text or number inputs into a standard integer score (1, 2, or 3).
    This handles data entry inconsistencies gracefully.
    Returns None if the value is empty or cannot be interpreted.
    """
    if pd.isna(value):
        return None

    # First, try to interpret the value as a number.
    try:
        num_val = float(str(value).strip())
        # Clamp the number between 1 and 3.
        return max(1, min(3, int(round(num_val))))
    except (ValueError, TypeError):
        pass

    # If it's not a number, try to match it against known text labels.
    s_val = str(value).strip().lower()
    
    # Mappings for different status texts (including Indonesian)
    score_map = {
        3: {"3", "good", "normal", "ok", "green", "pass", "low risk", "baik"},
        2: {"2", "fair", "medium", "moderate", "yellow", "alert", "cukup"},
        1: {"1", "bad", "poor", "fail", "red", "critical", "buruk", "need action", "action"},
    }

    for score, labels in score_map.items():
        if s_val in labels:
            return score
            
    return None # Return None if no match is found.


def score_to_status(score: float) -> str:
    """Converts a numeric score (1, 2, 3) to a color-coded status string."""
    if pd.isna(score):
        return "UNKNOWN"
    return {1: "RED", 2: "AMBER", 3: "GREEN"}.get(int(score), "UNKNOWN")


def color_status_cell(status: str):
    """Applies CSS styling to a cell based on its status for better visualization."""
    color_map = {
        "RED": "#ff4d4f",
        "AMBER": "#faad14",
        "GREEN": "#52c41a",
        "UNKNOWN": "#8c8c8c",
    }
    color = color_map.get(status, "#8c8c8c")
    return f"background-color: {color}; color: white; border-radius: 5px; text-align: center;"

# --- Main Application ---

# 1. File Upload
uploaded_file = st.file_uploader("Upload Excel file (must contain a 'Scorecard' sheet)", type=["xlsx", "xlsm"])

if not uploaded_file:
    st.info("👆 Please upload your Excel file to begin.")
    st.stop()

# 2. Load and Process Data
with st.spinner("Reading and processing your file..."):
    df = load_scorecard(uploaded_file)

    # --- Data Cleaning ---
    # Drop rows that are completely empty.
    df.dropna(how='all', inplace=True)
    # Drop rows where the essential 'EQUIPMENT DESCRIPTION' is missing.
    df.dropna(subset=["EQUIPMENT DESCRIPTION"], inplace=True)
    # Convert DATE column, handling potential errors gracefully.
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")

# 3. Sidebar Filters
st.sidebar.header("🔍 Filters")

# Create a copy of the dataframe for filtering.
df_filtered = df.copy()

# Date range filter
if df_filtered["DATE"].notna().any():
    min_date = df_filtered["DATE"].min().date()
    max_date = df_filtered["DATE"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Date range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )
    date_mask = (df_filtered["DATE"].dt.date >= start_date) & (df_filtered["DATE"].dt.date <= end_date)
    df_filtered = df_filtered[date_mask]
else:
    st.sidebar.caption("No valid dates found; skipping date filter.")

# Categorical filters
for col in ["AREA", "SYSTEM", "EQUIPMENT DESCRIPTION"]:
    unique_values = sorted(df_filtered[col].dropna().unique())
    selected_values = st.sidebar.multiselect(col, unique_values, default=unique_values)
    df_filtered = df_filtered[df_filtered[col].isin(selected_values)]

# --- Stop if filters result in no data ---
if df_filtered.empty:
    st.warning("No data matches your filter criteria. Please adjust the filters in the sidebar.")
    st.stop()

# 4. Scoring Logic
with st.spinner("Calculating scores..."):
    # Define the columns that contribute to the overall score.
    element_cols = ["VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION"]
    element_score_cols = [f"{col}_SCORE" for col in element_cols]

    # Calculate a numeric score for each element.
    for col in element_cols:
        df_filtered[f"{col}_SCORE"] = df_filtered[col].apply(coerce_score)

    # Calculate the fallback score from the main "CONDITION MONITORING SCORE" column.
    df_filtered["CMS_INPUT_SCORE"] = df_filtered["CONDITION MONITORING SCORE"].apply(coerce_score)

    # The final equipment score is the WORST (minimum) of the individual element scores.
    row_min_score = df_filtered[element_score_cols].min(axis=1, skipna=True)
    
    # If all element scores are empty, use the fallback score.
    df_filtered["EQUIP_SCORE"] = row_min_score.fillna(df_filtered["CMS_INPUT_SCORE"])
    df_filtered["EQUIP_STATUS"] = df_filtered["EQUIP_SCORE"].apply(score_to_status)

    # Aggregate scores up to the System and Area level (worst score wins).
    sys_scores = df_filtered.groupby(["AREA", "SYSTEM"])["EQUIP_SCORE"].min().reset_index()
    sys_scores["SYSTEM_STATUS"] = sys_scores["EQUIP_SCORE"].apply(score_to_status)
    
    area_scores = sys_scores.groupby("AREA")["EQUIP_SCORE"].min().reset_index()
    area_scores["AREA_STATUS"] = area_scores["EQUIP_SCORE"].apply(score_to_status)

# 5. Display KPIs
st.subheader("Dashboard Summary")
kpi_cols = st.columns(4)
kpi_cols[0].metric("Equipments (filtered)", len(df_filtered))
kpi_cols[1].metric("Systems (filtered)", sys_scores["SYSTEM"].nunique())
kpi_cols[2].metric("Areas (filtered)", area_scores["AREA"].nunique())

status_counts = df_filtered['EQUIP_STATUS'].value_counts()
red_count = status_counts.get('RED', 0)
amber_count = status_counts.get('AMBER', 0)
green_count = status_counts.get('GREEN', 0)
kpi_cols[3].metric(
    "Equip RED | AMBER | GREEN",
    f"{red_count} | {amber_count} | {green_count}",
)
st.divider()

# 6. Display Data Tables
st.subheader("Area Status")
st.dataframe(
    area_scores.style.applymap(color_status_cell, subset=["AREA_STATUS"]),
    use_container_width=True, hide_index=True
)

st.subheader("System Status")
st.dataframe(
    sys_scores.style.applymap(color_status_cell, subset=["SYSTEM_STATUS"]),
    use_container_width=True, hide_index=True
)

st.subheader("Equipment Details")
# Define which columns to show in the final detailed table.
cols_to_show = [
    "AREA", "SYSTEM", "EQUIPMENT DESCRIPTION", "DATE", "EQUIP_STATUS", "EQUIP_SCORE",
    "VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION"
]
# Filter out any columns that might not exist in the source file.
existing_cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]
equip_view = df_filtered[existing_cols_to_show].sort_values(
    ["AREA", "SYSTEM", "EQUIPMENT DESCRIPTION", "DATE"], na_position="last"
)
st.dataframe(
    equip_view.style.applymap(color_status_cell, subset=["EQUIP_STATUS"]),
    use_container_width=True, hide_index=True
)

# 7. Download Button
csv_data = equip_view.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇ Download Filtered Data (CSV)",
    data=csv_data,
    file_name="filtered_equipment_data.csv",
    mime="text/csv",
)

# --- Footer ---
st.caption(
    "Scoring Rule: Equipment score is the worst (minimum) of its component scores (Vibration, Oil, etc.). "
    "If all components are missing, it falls back to the 'Condition Monitoring Score'. "
    "System/Area status reflects the worst score within that group."
)
