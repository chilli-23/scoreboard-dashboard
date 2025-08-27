import streamlit as st
import pandas as pd
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="Equipment Condition Dashboard", layout="wide")

# --- Custom CSS to make sidebar buttons look like links ---
st.markdown("""
<style>
    /* Target buttons within the sidebar */
    [data-testid="stSidebar"] button {
        background: none !important;
        border: none;
        padding: 0 !important;
        margin: 0 !important;
        font-size: 1rem; /* Match Streamlit's default font size */
        color: white !important; /* Set text color */
        text-decoration: none;
        cursor: pointer;
        text-align: left;
        width: 100%;
        margin-bottom: 0.5rem; /* Add space between the links */
    }
    /* Add a hover effect */
    [data-testid="stSidebar"] button:hover {
        text-decoration: underline;
        color: #FF4B4B !important; /* Streamlit's accent color for hover */
    }
    /* Remove the default focus outline */
    [data-testid="stSidebar"] button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)


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

# --- Page Implementations ---

def upload_page():
    """Defines the content of the file upload page, protected by a password."""
    st.title("📂 Upload Data")

    # --- Password Protection ---
    if not st.session_state.get("authenticated", False):
        password = st.text_input("Enter Password to Upload", type="password")
        if password:
            if password == "123456": # Test password
                st.session_state.authenticated = True
                st.rerun() # Rerun the script to show the uploader
            else:
                st.error("Incorrect password.")
        st.stop() # Stop execution if not authenticated

    # --- File Uploader (only shown if authenticated) ---
    st.info("Please upload your Excel file to begin. The sheet must be named 'Scorecard'.")
    
    uploaded_file = st.file_uploader(
        "Upload Excel file", 
        type=["xlsx", "xlsm"], 
        label_visibility="collapsed"
    )

    if uploaded_file:
        with st.spinner("Reading and processing your file..."):
            df = load_scorecard(uploaded_file)
            # --- Data Cleaning ---
            df.dropna(how='all', inplace=True)
            df.dropna(subset=["EQUIPMENT DESCRIPTION"], inplace=True)
            df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
            
            # Store the processed dataframe in the session state
            st.session_state.df = df
            st.success("✅ File processed successfully! Navigate to the Dashboard to view the data.")
            # Reset authentication after successful upload
            st.session_state.authenticated = False

def dashboard_page():
    """Defines the content of the main dashboard page."""
    st.title("📊 Equipment Condition Dashboard")

    if st.session_state.df is None:
        st.warning("No data found. Please go to the 'Upload Data' page to upload a file first.")
        st.stop()

    df = st.session_state.df.copy()
    df_filtered = df.copy()

    # --- Main Page Filters ---
    with st.expander("🔍 Show/Hide Filters", expanded=True):
        filter_cols = st.columns(2)
        
        with filter_cols[0]:
            # Date range filter
            if df["DATE"].notna().any():
                min_date = df["DATE"].min().date()
                max_date = df["DATE"].max().date()
                # Default the date range to only the latest date
                start_date, end_date = st.date_input(
                    "Filter by Date Range",
                    [max_date, max_date], # Default to latest date
                    min_value=min_date,
                    max_value=max_date,
                )
                date_mask = (df_filtered["DATE"].dt.date >= start_date) & (df_filtered["DATE"].dt.date <= end_date)
                df_filtered = df_filtered[date_mask]
            else:
                st.caption("No valid dates found for filtering.")

        with filter_cols[1]:
            # Area and System filters
            area_values = sorted(df_filtered["AREA"].dropna().unique())
            selected_areas = st.multiselect("Filter by Area", area_values, default=area_values)
            df_filtered = df_filtered[df_filtered["AREA"].isin(selected_areas)]
            
            system_values = sorted(df_filtered["SYSTEM"].dropna().unique())
            # Add an "All Systems" option to the beginning of the list
            system_options = ["All Systems"] + system_values
            selected_system = st.selectbox("Filter by System", system_options)
            
            # Apply the filter only if a specific system is chosen
            if selected_system != "All Systems":
                df_filtered = df_filtered[df_filtered["SYSTEM"] == selected_system]

    if df_filtered.empty:
        st.warning("No data matches your filter criteria. Please adjust the filters.")
        st.stop()

    # --- Scoring Logic ---
    with st.spinner("Calculating scores..."):
        element_cols = ["VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION"]
        element_score_cols = [f"{col}_SCORE" for col in element_cols]
        for col in element_cols:
            df_filtered[f"{col}_SCORE"] = df_filtered[col].apply(coerce_score)
        df_filtered["CMS_INPUT_SCORE"] = df_filtered["CONDITION MONITORING SCORE"].apply(coerce_score)
        row_min_score = df_filtered[element_score_cols].min(axis=1, skipna=True)
        df_filtered["EQUIP_SCORE"] = row_min_score.fillna(df_filtered["CMS_INPUT_SCORE"])
        df_filtered["EQUIP_STATUS"] = df_filtered["EQUIP_SCORE"].apply(score_to_status)
        sys_scores = df_filtered.groupby(["AREA", "SYSTEM"])["EQUIP_SCORE"].min().reset_index()
        sys_scores["SYSTEM_STATUS"] = sys_scores["EQUIP_SCORE"].apply(score_to_status)
        area_scores = sys_scores.groupby("AREA")["EQUIP_SCORE"].min().reset_index()
        area_scores["AREA_STATUS"] = area_scores["EQUIP_SCORE"].apply(score_to_status)

    st.divider()

    # --- Display Data Tables ---
    st.subheader("Area Status")
    # Format the score to be an integer before displaying
    area_scores['EQUIP_SCORE'] = area_scores['EQUIP_SCORE'].apply(lambda x: int(x) if pd.notna(x) else '')
    st.dataframe(
        area_scores.style.applymap(color_status_cell, subset=["AREA_STATUS"]),
        use_container_width=True, hide_index=True
    )
    st.subheader("System Status")
    # Format the score to be an integer before displaying
    sys_scores['EQUIP_SCORE'] = sys_scores['EQUIP_SCORE'].apply(lambda x: int(x) if pd.notna(x) else '')
    st.dataframe(
        sys_scores.style.applymap(color_status_cell, subset=["SYSTEM_STATUS"]),
        use_container_width=True, hide_index=True
    )
    st.subheader("Equipment Details")
    cols_to_show = [
        "EQUIPMENT DESCRIPTION", "EQUIP_STATUS", "EQUIP_SCORE",
        "VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION"
    ]
    existing_cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]
    equip_view = df_filtered[existing_cols_to_show].sort_values(
        ["EQUIPMENT DESCRIPTION"], na_position="last"
    )
    
    # Format the score to be an integer
    equip_view['EQUIP_SCORE'] = equip_view['EQUIP_SCORE'].apply(lambda x: int(x) if pd.notna(x) else '')

    st.dataframe(
        equip_view.style.applymap(color_status_cell, subset=["EQUIP_STATUS"]),
        use_container_width=True, hide_index=True
    )

    # --- Download Button ---
    csv_data = equip_view.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Filtered Data (CSV)",
        data=csv_data,
        file_name="filtered_equipment_data.csv",
        mime="text/csv",
    )
    st.caption(
        "Scoring Rule: Equipment score is the worst (minimum) of its component scores. "
        "If all components are missing, it falls back to the 'Condition Monitoring Score'. "
        "System/Area status reflects the worst score within that group."
    )

# --- Main Application Logic ---

# Initialize session state for the dataframe, current page, and authentication status
if 'df' not in st.session_state:
    st.session_state.df = None
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard" # Default to dashboard
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Sidebar Navigation
st.sidebar.title("Navigation")

# When a button is clicked, it returns True for one run. We use this to update the page state.
if st.sidebar.button("📂 Upload Data"):
    st.session_state.page = "Upload Data"
    # When navigating to upload, reset authentication
    st.session_state.authenticated = False
    st.rerun()

if st.sidebar.button("📊 Dashboard"):
    st.session_state.page = "Dashboard"
    st.rerun()

# Display the selected page based on the value in session state
if st.session_state.page == "Upload Data":
    upload_page()
elif st.session_state.page == "Dashboard":
    dashboard_page()
