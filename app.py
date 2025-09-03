import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
import requests
import io

# =========================
# Helper functions
# =========================
def map_status(score):
    if score == 1:
        return "Need Action"
    elif score == 2:
        return "Caution"
    elif score == 3:
        return "Okay"
    return "UNKNOWN"

def color_score(val):
    if pd.isna(val):
        return ""
    try:
        v = int(val)
    except Exception:
        return ""
    if v == 1:
        return "background-color: red; color: white;"
    elif v == 2:
        return "background-color: yellow; color: black;"
    elif v == 3:
        return "background-color: green; color: white;"
    return ""

# =========================
# Main Streamlit App
# =========================
def main():
    st.set_page_config(layout="wide")
    st.title("📊 Condition Monitoring Dashboard")

    RAW_FILE_URL = "https://raw.githubusercontent.com/AlvinWinarta2111/equipment-monitoring-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

    @st.cache_data(ttl=300)
    def load_data():
        response = requests.get(RAW_FILE_URL)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name="Scorecard", header=1)

    try:
        df = load_data()
    except Exception as e:
        st.error(f"Error reading data from GitHub file: {e}")
        return

    df.columns = [col.strip().upper() for col in df.columns]
    if "CONDITION MONITORING SCORE" not in df.columns:
        st.error("Error: 'CONDITION MONITORING SCORE' column not found.")
        return

    df = df.rename(columns={"CONDITION MONITORING SCORE": "SCORE"})
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    for col in ['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION']:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.strip().str.upper()

    df.dropna(subset=['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE'], inplace=True)
    df["SCORE"] = df["SCORE"].astype(int)
    df = df[df["SCORE"].isin([1, 2, 3])]
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    # --- Filter tanggal
    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df_filtered = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]
    else:
        df_filtered = df

    if df_filtered.empty:
        st.warning("No data available for the selected date range.")
        return

    # --- Sistem explorer
    st.subheader("System Status Explorer")
    system_summary = df_filtered.groupby("SYSTEM").agg({"SCORE": "min"}).reset_index()
    system_summary["STATUS"] = system_summary["SCORE"].apply(map_status)
    gb = GridOptionsBuilder.from_dataframe(system_summary[["SYSTEM", "STATUS", "SCORE"]])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gridOptions = gb.build()
    system_grid = AgGrid(system_summary, gridOptions=gridOptions,
                         update_mode=GridUpdateMode.SELECTION_CHANGED,
                         fit_columns_on_grid_load=True,
                         height=300, theme="streamlit")

    selected_system_rows = system_grid.get("selected_rows", [])
    if selected_system_rows:
        selected_system = selected_system_rows[0]["SYSTEM"]

        st.markdown(f"### Equipment in **{selected_system}**")
        detail_df = df_filtered[df_filtered["SYSTEM"] == selected_system].copy()
        detail_df = detail_df.sort_values(by="DATE", ascending=False).drop_duplicates("EQUIPMENT DESCRIPTION")
        detail_df["STATUS"] = detail_df["SCORE"].apply(map_status)

        gb_details = GridOptionsBuilder.from_dataframe(detail_df[["EQUIPMENT DESCRIPTION", "DATE", "SCORE", "STATUS"]])
        gb_details.configure_selection(selection_mode="single", use_checkbox=False)
        gridOptions_details = gb_details.build()
        detail_grid = AgGrid(detail_df, gridOptions=gridOptions_details,
                             update_mode=GridUpdateMode.SELECTION_CHANGED,
                             fit_columns_on_grid_load=True,
                             height=300, theme="streamlit")

        selected_equipment_rows = detail_grid.get("selected_rows", [])
        if selected_equipment_rows:
            selected_equip = selected_equipment_rows[0]["EQUIPMENT DESCRIPTION"]

            st.markdown(f"#### Trend for: **{selected_equip}**")
            df_equip = df_filtered[df_filtered["EQUIPMENT DESCRIPTION"] == selected_equip].copy()
            if not df_equip.empty:
                fig_trend = px.line(df_equip, x="DATE", y="SCORE", markers=True,
                                    title=f"Performance Trend for {selected_equip}")
                fig_trend.update_layout(yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1))
                st.plotly_chart(fig_trend, use_container_width=True)

                # === NEW: Table untuk pilih tanggal ===
                st.subheader("Historical Records")
                df_equip = df_equip.sort_values("DATE", ascending=False)
                df_equip["STATUS"] = df_equip["SCORE"].apply(map_status)

                gb_hist = GridOptionsBuilder.from_dataframe(df_equip[["DATE", "SCORE", "STATUS", "FINDING", "ACTION PLAN"]])
                gb_hist.configure_selection(selection_mode="single", use_checkbox=False)
                gridOptions_hist = gb_hist.build()
                hist_grid = AgGrid(df_equip, gridOptions=gridOptions_hist,
                                   update_mode=GridUpdateMode.SELECTION_CHANGED,
                                   fit_columns_on_grid_load=True,
                                   height=300, theme="streamlit")

                selected_hist_rows = hist_grid.get("selected_rows", [])
                if selected_hist_rows:
                    row = selected_hist_rows[0]
                    st.markdown(f"### Details for {selected_equip} on {row['DATE']:%d-%m-%Y}")
                    st.write(f"**Score:** {row['SCORE']}")
                    st.write(f"**Status:** {row['STATUS']}")
                    st.write(f"**Finding:** {row.get('FINDING', 'N/A')}")
                    st.write(f"**Action Plan:** {row.get('ACTION PLAN', 'N/A')}")

if __name__ == "__main__":
    main()
