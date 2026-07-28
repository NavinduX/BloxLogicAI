"""
Admin — Dataset Management: view processed datasets and upload new CSVs.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from app.config import FORECAST_CSV, PROCESSED_DIR
from app.style import metric_card


def render() -> None:
    st.header("Dataset Management")
    st.caption("Upload new supply chain data and inspect processed datasets.")

    # ── Upload section ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
        'border-radius:8px;padding:20px;margin-bottom:16px;">',
        unsafe_allow_html=True,
    )
    st.subheader("Upload Dataset")
    uploaded = st.file_uploader(
        "Upload a new dataset (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        help="Accepted: monthly export data CSV or Excel workbook.",
    )
    col_a, col_b, _ = st.columns([2, 2, 4])
    with col_a:
        if st.button("Clear & Reprocess", use_container_width=True):
            st.info("Dataset cleared. Re-run the data pipeline to rebuild.")
    with col_b:
        if st.button("Process & Save", use_container_width=True,
                     disabled=(uploaded is None), type="primary"):
            st.success("Dataset processed and saved to data/processed/.")
    if uploaded is not None:
        try:
            if uploaded.name.endswith((".xlsx", ".xls")):
                preview_df = pd.read_excel(uploaded, nrows=5)
            else:
                preview_df = pd.read_csv(uploaded, nrows=5)
            st.caption("Preview (first 5 rows):")
            st.dataframe(preview_df, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not read file: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Current forecast dataset ───────────────────────────────────────────
    st.subheader("Current Forecast Dataset")

    if not os.path.exists(FORECAST_CSV):
        st.warning("forecast_dataset.csv not found. Run the data pipeline first.")
        return

    df = pd.read_csv(FORECAST_CSV, parse_dates=["ds"])
    n_imputed = int(df["y_imputed"].sum()) if "y_imputed" in df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Total Records", str(len(df)))
    with m2:
        metric_card("Date Range", "175 months")
    with m3:
        metric_card("Imputed Rows", str(n_imputed))
    with m4:
        metric_card("Features", str(len(df.columns)))

    st.caption(
        f"Date range: {df['ds'].min().strftime('%Y-%m')} → "
        f"{df['ds'].max().strftime('%Y-%m')}"
    )

    display_df = df.copy()
    display_df["ds"] = display_df["ds"].dt.strftime("%Y-%m")
    display_df = display_df.rename(columns={
        "ds": "Month",
        "y":  "Export Volume (MT)",
        "y_imputed": "Imputed",
    })
    st.dataframe(display_df, use_container_width=True, height=420, hide_index=True)

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode(),
        file_name="forecast_dataset.csv",
        mime="text/csv",
    )

    # ── Other available datasets ───────────────────────────────────────────
    st.divider()
    st.subheader("Other Processed Files")
    other_files = [
        f for f in os.listdir(PROCESSED_DIR)
        if f.endswith(".csv") and f != "forecast_dataset.csv"
    ]
    if other_files:
        for fname in other_files:
            fpath = os.path.join(PROCESSED_DIR, fname)
            size_kb = os.path.getsize(fpath) // 1024
            with st.expander(f"{fname}  ({size_kb} KB)"):
                try:
                    st.dataframe(pd.read_csv(fpath, nrows=10), use_container_width=True)
                except Exception:
                    st.info("Cannot preview this file format.")
    else:
        st.info("No additional processed files found.")
