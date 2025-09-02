import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from streamlit_plotly_events import plotly_events
import requests
import io

# =========================
# Helper functions
# =========================

def map_status(score):
    """Converts a numeric score (1, 2, 3) to a text status."""
    if score == 1:
        return "Need Action"
    elif score == 2:
        return "Caution"
    elif score == 3:
        return "Okay"
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
    if val == "Need Action":
        return "background-color: red; color
