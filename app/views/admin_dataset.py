"""
Admin — Dataset Management: view processed datasets and upload new CSVs.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from app.config import FORECAST_CSV, MV_FORECAST_CSV, ANOMALY_CSV, PROCESSED_DIR
from app.style import metric_card


def merge_and_retrain(uploaded_file, target_csv, required_cols, model_type):
    try:
        new_df = pd.read_csv(uploaded_file)
        
        missing = [col for col in required_cols if col not in new_df.columns]
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
            return
            
        if not os.path.exists(target_csv):
            st.error(f"Target dataset {os.path.basename(target_csv)} not found.")
            return
            
        current_df = pd.read_csv(target_csv)
        
        date_col = "ds" if model_type in ["univariate", "multivariate"] else "month"
        
        new_df[date_col] = pd.to_datetime(new_df[date_col]).dt.strftime('%Y-%m-%d')
        current_df[date_col] = pd.to_datetime(current_df[date_col]).dt.strftime('%Y-%m-%d')
        
        combined_df = pd.concat([current_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=[date_col], keep="last")
        combined_df = combined_df.sort_values(by=date_col).reset_index(drop=True)
        
        combined_df.to_csv(target_csv, index=False)
        st.success(f"Successfully merged new data into {os.path.basename(target_csv)}.")
        
        with st.spinner(f"Retraining {model_type} model..."):
            if model_type == "univariate":
                from models.forecasting import run_univariate_model, load_forecast_data
                run_univariate_model(load_forecast_data(target_csv))
            elif model_type == "multivariate":
                from models.forecasting import run_multivariate_model, load_multivariate_data
                run_multivariate_model(load_multivariate_data(target_csv))
            elif model_type == "anomaly":
                from models.anomaly import run_anomaly_detection
                run_anomaly_detection()
                
        st.success(f"{model_type.capitalize()} model retrained successfully!")
        
    except Exception as exc:
        st.error(f"An error occurred: {exc}")


def render() -> None:
    st.header("Dataset Management")
    st.caption("Upload new supply chain data and inspect processed datasets.")

    t1, t2, t3, t4 = st.tabs(["Univariate Forecast", "Multivariate Forecast", "Anomaly Detection", "Other Files"])
    
    with t1:
        st.subheader("Upload Monthly Data Updates")
        st.info("Upload new monthly data for the Univariate Forecast model. The CSV should contain only the new month's data.")
        uploaded_uni = st.file_uploader(
            "Upload Univariate CSV",
            type=["csv"],
            help="Required columns: ds, y, y_imputed",
            key="upload_uni"
        )
        if st.button("Merge & Retrain Univariate Model", disabled=(uploaded_uni is None), type="primary"):
            merge_and_retrain(uploaded_uni, FORECAST_CSV, ["ds", "y", "y_imputed"], "univariate")
            
        st.divider()
        st.subheader("Current Forecast Dataset")

        if not os.path.exists(FORECAST_CSV):
            st.warning("forecast_univariant.csv not found. Run the data pipeline first.")
        else:
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
                file_name="forecast_univariant.csv",
                mime="text/csv",
            )
            
    with t2:
        st.subheader("Upload Monthly Data Updates")
        st.info("Upload new monthly data for the Multivariate Forecast model. The CSV should contain only the new month's data.")
        uploaded_multi = st.file_uploader(
            "Upload Multivariate CSV",
            type=["csv"],
            help="Required columns: ds, y, production_mt, usd_lkr_avg, rainfall_mm, temp_mean",
            key="upload_multi"
        )
        if st.button("Merge & Retrain Multivariate Model", disabled=(uploaded_multi is None), type="primary"):
            merge_and_retrain(uploaded_multi, MV_FORECAST_CSV, ["ds", "y", "production_mt", "usd_lkr_avg", "rainfall_mm", "temp_mean"], "multivariate")

        st.divider()
        st.subheader("Multivariate Forecast Dataset")

        if not os.path.exists(MV_FORECAST_CSV):
            st.warning("forecast_multivariant.csv not found.")
        else:
            df_mv = pd.read_csv(MV_FORECAST_CSV, parse_dates=["ds"])
            n_imputed_mv = int(df_mv["y_imputed"].sum()) if "y_imputed" in df_mv.columns else 0

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_card("Total Records", str(len(df_mv)))
            with m2:
                metric_card("Date Range", "175 months")
            with m3:
                metric_card("Imputed Rows", str(n_imputed_mv))
            with m4:
                metric_card("Features", str(len(df_mv.columns)))

            st.caption(
                f"Date range: {df_mv['ds'].min().strftime('%Y-%m')} → "
                f"{df_mv['ds'].max().strftime('%Y-%m')}"
            )
            display_df_mv = df_mv.copy()
            display_df_mv["ds"] = display_df_mv["ds"].dt.strftime("%Y-%m")
            st.dataframe(display_df_mv, use_container_width=True, height=300, hide_index=True)
            
    with t3:
        st.subheader("Upload Monthly Data Updates")
        st.info("Upload new monthly data for Anomaly Detection. The CSV should contain only the new month's data.")
        uploaded_anom = st.file_uploader(
            "Upload Anomaly CSV",
            type=["csv"],
            help="Required columns: month, production_mt, export_mt, usd_lkr_avg, usd_lkr_volatility, rainfall_mm, temp_mean, crude_oil_price, brent_crude_price, fuel_lp92, fuel_lad, kerosene_price, export_derived",
            key="upload_anom"
        )
        if st.button("Merge & Retrain Anomaly Model", disabled=(uploaded_anom is None), type="primary"):
            merge_and_retrain(uploaded_anom, ANOMALY_CSV, ["month", "production_mt", "export_mt", "usd_lkr_avg", "usd_lkr_volatility", "rainfall_mm", "temp_mean", "crude_oil_price", "brent_crude_price", "fuel_lp92", "fuel_lad", "kerosene_price", "export_derived"], "anomaly")

        st.divider()
        st.subheader("Anomaly Detection Dataset")

        if not os.path.exists(ANOMALY_CSV):
            st.warning("anomaly_detection.csv not found.")
        else:
            df_an = pd.read_csv(ANOMALY_CSV)
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_card("Total Records", str(len(df_an)))
            with m2:
                metric_card("Date Range", "165 months")
            with m3:
                metric_card("Imputed Rows", "0")
            with m4:
                metric_card("Features", str(len(df_an.columns)))

            st.caption(
                f"Date range: {pd.to_datetime(df_an['month']).min().strftime('%Y-%m')} → "
                f"{pd.to_datetime(df_an['month']).max().strftime('%Y-%m')}"
            )
            display_df_an = df_an.copy()
            st.dataframe(display_df_an, use_container_width=True, height=300, hide_index=True)

    with t4:
        st.subheader("Other Processed Files")
        other_files = [
            f for f in os.listdir(PROCESSED_DIR)
            if f.endswith(".csv") and f not in ["forecast_univariant.csv", "forecast_multivariant.csv", "anomaly_detection.csv"]
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
