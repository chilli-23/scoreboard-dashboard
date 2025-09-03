import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# -----------------------
# Load Excel from GitHub
# -----------------------
RAW_FILE_URL = "https://raw.githubusercontent.com/chilli-23/scoreboard-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

@st.cache_data
def load_data():
    try:
        # Fetch file from GitHub
        url = RAW_FILE_URL.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        content = requests.get(url).content
        df = pd.read_excel(io.BytesIO(content))

        # Normalize column names
        df.columns = df.columns.str.strip().str.upper()

        # Rename common variations
        rename_map = {
            "SCORECARD": "SCORE",
            "SCORE (%)": "SCORE",
            "DATE ": "DATE",
            " EQUIPMENT DESCRIPTION": "EQUIPMENT DESCRIPTION"
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

        # Check required columns
        required_cols = ["DATE", "SCORE", "EQUIPMENT DESCRIPTION"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"❌ Missing required column: {col}")
                return pd.DataFrame()

        # Convert types
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")

        # Drop invalid rows
        df.dropna(subset=["DATE", "SCORE"], inplace=True)

        return df
    except Exception as e:
        st.error(f"⚠️ Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

st.title("📊 Condition Monitoring Scoreboard")

if df.empty:
    st.warning("No data available. Please check your Excel file.")
else:
    # Show available equipment list
    equipment_list = df["EQUIPMENT DESCRIPTION"].dropna().unique().tolist()
    selected_equipment = st.selectbox("Select Equipment:", equipment_list)

    filtered_df = df[df["EQUIPMENT DESCRIPTION"] == selected_equipment]

    if filtered_df.empty:
        st.warning("No data available for the selected equipment.")
    else:
        # -----------------------
        # Plot EXACT values only (scatter)
        # -----------------------
        fig = px.scatter(
            filtered_df,
            x="DATE",
            y="SCORE",
            title=f"Score Trend for {selected_equipment}",
            markers=True
        )

        fig.update_traces(marker=dict(size=10, color="black"))

        st.plotly_chart(fig, use_container_width=True)

        # Show raw data for verification
        st.subheader("Raw Data")
        st.dataframe(filtered_df)
