import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode

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
    """Returns CSS style for SCORE cells (used in pandas Styler)."""
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

def color_status(val):
    """Returns CSS style for STATUS cells (used in pandas Styler)."""
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

    # Normalize column names to UPPER
    df.columns = [col.strip().upper() for col in df.columns]

    # Ensure required column exists
    if "CONDITION MONITORING SCORE" not in df.columns:
        st.error("Error: A column named 'CONDITION MONITORING SCORE' was not found in your file.")
        return

    # Rename and coerce types
    df = df.rename(columns={"CONDITION MONITORING SCORE": "SCORE"})
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Drop rows missing essential fields
    required_subset = ['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE']
    df.dropna(subset=required_subset, inplace=True)

    # Convert SCORE to integer (safe now because we dropped NaNs)
    df["SCORE"] = df["SCORE"].astype(int)

    # Create text status for pie charts
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    # --- FILTERS ---
    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df_filtered_by_date = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]
    else:
        df_filtered_by_date = df # Default to all data if range is incomplete

    if df_filtered_by_date.empty:
        st.warning("No data available for the selected date range.")
        return

    # --- Aggregation ---
    system_scores = df_filtered_by_date.groupby(["AREA", "SYSTEM"])["SCORE"].min().reset_index()
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

    # ======================
    # 🥧 PIE CHARTS
    # ======================
    st.subheader("Equipment Status Distribution per AREA")
    # Use the latest status for the pie charts within the date range
    latest_for_pie = df_filtered_by_date.sort_values("DATE").groupby("EQUIPMENT DESCRIPTION", as_index=False).last()
    area_dist = latest_for_pie.groupby(["AREA", "EQUIP_STATUS"])["EQUIPMENT DESCRIPTION"].count().reset_index(name="COUNT")
    areas = sorted(area_dist["AREA"].unique())

    cols_per_row = 3
    for i in range(0, len(areas), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, area in enumerate(areas[i:i+cols_per_row]):
            if j < len(cols):
                with cols[j]:
                    st.markdown(f"**{area}**")
                    area_data = area_dist[area_dist["AREA"] == area]
                    fig = px.pie(
                        area_data, names="EQUIP_STATUS", values="COUNT",
                        color="EQUIP_STATUS",
                        color_discrete_map={"RED": "red", "AMBER": "yellow", "GREEN": "green"},
                        hole=0.4
                    )
                    fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)

    # ======================
    # SYSTEM Score Distribution
    # ======================
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
    # Area Status (table)
    # ======================
    st.subheader("Area Status (Lowest Score)")
    st.dataframe(area_scores.style.map(color_score, subset=["SCORE"]).hide(axis="index"))

    # ======================
    # 📍 SYSTEM STATUS EXPLORER (Summary + Drilldown)
    # ======================
    st.subheader("System Status Explorer")

    # --- Table 1: System Summary ---
    system_summary = (
        df_filtered_by_date.groupby("SYSTEM")
        .agg({"SCORE": "min"})
        .reset_index()
    )
    system_summary["STATUS"] = system_summary["SCORE"].apply(map_status)

    gb = GridOptionsBuilder.from_dataframe(system_summary[["SYSTEM", "STATUS", "SCORE"]])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(resizable=True, filter=True, sortable=True)
    gridOptions = gb.build()

    grid_response = AgGrid(
        system_summary,
        gridOptions=gridOptions,
        enable_enterprise_modules=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        height=300
    )

    # --- Table 2: Equipment Details (only if a system is clicked) ---
    selected = grid_response.get("selected_rows", [])

    if isinstance(selected, pd.DataFrame):
        selected = selected.to_dict("records")
    
    if selected:
        selected_system = selected[0].get("SYSTEM")

        if selected_system:
            st.markdown(f"### Equipment Details for **{selected_system}** (Latest Status in Range)")

            # Filter the date-ranged data for the selected system
            detail_df = df_filtered_by_date[df_filtered_by_date["SYSTEM"] == selected_system].copy()
            
            # Find the latest record for each piece of equipment within that system
            detail_df = detail_df.sort_values(by="DATE", ascending=False)
            detail_df = detail_df.drop_duplicates(subset=["EQUIPMENT DESCRIPTION"], keep="first")

            detail_df["DATE"] = detail_df["DATE"].dt.strftime('%d-%m-%Y')
            detail_df["STATUS"] = detail_df["SCORE"].apply(map_status)

            display_cols = [
                "EQUIPMENT DESCRIPTION", "DATE", "SCORE", "STATUS",
                "VIBRATION", "OIL ANALYSIS", "TEMPERATURE",
                "OTHER INSPECTION", "FINDING", "ACTION PLAN"
            ]
            display_cols = [c for c in display_cols if c in detail_df.columns]

            st.dataframe(
                detail_df[display_cols].style.map(color_score, subset=["SCORE"]).hide(axis="index"),
                use_container_width=True
            )

            # ======================
            # 📈 PERFORMANCE TREND (NOW LINKED TO SELECTION)
            # ======================
            st.subheader(f"Performance Trend for {selected_system}")
            
            # Use the date-filtered dataframe for the trend
            trend_df = df_filtered_by_date.groupby(['DATE', 'SYSTEM'])['SCORE'].min().reset_index()
            
            # Filter the trend data for the selected system from the AgGrid table
            trend_df_filtered = trend_df[trend_df["SYSTEM"] == selected_system]

            if not trend_df_filtered.empty:
                fig_trend = px.line(
                    trend_df_filtered, x="DATE", y="SCORE", markers=True,
                    title=f"Performance Trend for {selected_system}"
                )
                fig_trend.update_layout(yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1))
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.warning(f"No trend data available for {selected_system} in the selected date range.")

    else:
        st.info("Click a system above to see its latest equipment details and performance trend.")


if __name__ == "__main__":
    main()
