# --- Performance Trend ---
st.subheader(f"Performance Trend for {selected_equip_name}")

df_equip = df_filtered_by_date[df_filtered_by_date["EQUIPMENT DESCRIPTION"] == selected_equip_name].copy()
if not df_equip.empty:
    # Take the lowest score for each date
    idx = df_equip.groupby("DATE")["SCORE"].idxmin()
    aggregated_df = df_equip.loc[idx].reset_index(drop=True)

    # Recompute status after aggregation
    aggregated_df["EQUIP_STATUS"] = aggregated_df["SCORE"].apply(map_status)

    # Plot trend
    fig_trend = px.line(
        aggregated_df,
        x="DATE",
        y="SCORE",
        markers=True,
        title=f"Trendline for {selected_equip_name}"
    )
    fig_trend.update_xaxes(tickformat="%d/%m/%y", fixedrange=True)
    fig_trend.update_layout(
        yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1, fixedrange=True)
    )

    st.plotly_chart(fig_trend, use_container_width=True)

    # Capture clicks
    selected_points = plotly_events(
        fig_trend,
        click_event=True,
        key=f"trend_chart_{selected_equip_name}"
    )

    if selected_points:
        clicked_date = pd.to_datetime(selected_points[0]["x"]).normalize()
        selected_row = aggregated_df[aggregated_df["DATE"].dt.normalize() == clicked_date].iloc[0]

        st.subheader(f"Details for {selected_equip_name} on {selected_row['DATE'].strftime('%d-%m-%Y')}")
        st.markdown(f"**Score:** {selected_row['SCORE']}")
        st.markdown(f"**Status:** {selected_row['EQUIP_STATUS']}")
        st.markdown(f"**Finding:** {selected_row.get('FINDING', 'N/A')}")
        st.markdown(f"**Action Plan:** {selected_row.get('ACTION PLAN', 'N/A')}")
    else:
        st.info("Click a point on the trend chart to see details for that specific date.")
else:
    st.warning(f"No trend data available for {selected_equip_name} in the selected date range.")
