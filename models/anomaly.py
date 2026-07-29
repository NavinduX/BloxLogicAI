"""
Anomaly Detection module using Isolation Forest.
"""

from __future__ import annotations

import json
import os
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.config import ANOMALY_PATH, ANOMALY_CSV

def run_anomaly_detection(contamination: float = 0.10, random_state: int = 42) -> int:
    """
    Run Isolation Forest on the anomaly dataset, save alerts to JSON.
    Returns the number of anomalies found.
    """
    if not os.path.exists(ANOMALY_CSV):
        return 0
    df = pd.read_csv(ANOMALY_CSV)
    
    # We parse the month string back to datetime to format it correctly later
    df["month"] = pd.to_datetime(df["month"])
    
    if df.empty:
        return 0

    feature_cols = ["production_mt", "export_mt", "usd_lkr_avg", "usd_lkr_volatility",
                    "rainfall_mm", "temp_mean", "crude_oil_price",
                    "brent_crude_price", "fuel_lp92", "fuel_lad", "kerosene_price"]

    # Filter only available columns (just in case)
    features = [c for c in feature_cols if c in df.columns]
    
    # Isolation Forest
    model = IsolationForest(contamination=contamination, random_state=random_state)
    df["anomaly"] = model.fit_predict(df[features])

    anomalies = df[df["anomaly"] == -1].copy()

    alerts = []
    for _, row in anomalies.iterrows():
        month_str = row["month"].strftime("%Y-%m")
        
        # Simple heuristics for severity and type
        severity = "MEDIUM"
        alert_type = "Supply Chain Disruption"
        
        if row["export_mt"] < df["export_mt"].quantile(0.10):
            severity = "HIGH"
            alert_type = "Severe Export Drop"
        elif row.get("fuel_lad", 0) > df.get("fuel_lad", pd.Series([0])).quantile(0.90):
            severity = "HIGH"
            alert_type = "Fuel Price Spike"
        elif row.get("crude_oil_price", 0) > df.get("crude_oil_price", pd.Series([0])).quantile(0.90):
            severity = "MEDIUM"
            alert_type = "Crude Oil Spike"
            
        desc = (f"Anomaly detected in {month_str}. "
                f"Export: {row['export_mt']:.0f} MT, "
                f"Production: {row['production_mt']:.0f} MT, "
                f"USD/LKR: {row['usd_lkr_avg']:.2f}, "
                f"Crude Oil: ${row.get('crude_oil_price', 0):.2f}, "
                f"Fuel (LAD): Rs.{row.get('fuel_lad', 0):.2f}.")
                
        action = "Review market conditions, check fuel availability, and adjust short-term export targets."
        
        alerts.append({
            "severity": severity,
            "type": alert_type,
            "date": month_str,
            "description": desc,
            "action": action
        })

    # Sort alerts by date descending
    alerts.sort(key=lambda x: x["date"], reverse=True)

    os.makedirs(os.path.dirname(ANOMALY_PATH), exist_ok=True)
    with open(ANOMALY_PATH, "w", encoding="utf-8") as fh:
        json.dump(alerts, fh, indent=2)

    return len(alerts)
