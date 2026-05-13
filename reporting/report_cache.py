# reporting/report_cache.py

from __future__ import annotations

import streamlit as st

from reporting.excel_report import build_excel_report
from utils.models import AnalysisResult


@st.cache_data(show_spinner=False)
def build_excel_report_cached(result: AnalysisResult) -> bytes:
    return build_excel_report(result)