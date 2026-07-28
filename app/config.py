"""
Centralized path constants — single source of truth for all file locations.
Import from here instead of computing ROOT in each module.
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # BloxLogicAI/

DATA_DIR      = os.path.join(ROOT, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODELS_DIR    = os.path.join(ROOT, "models", "saved")

FORECAST_CSV  = os.path.join(PROCESSED_DIR, "forecast_dataset.csv")
ANOMALY_PATH  = os.path.join(DATA_DIR, "anomaly_alerts.json")
LEDGER_PATH   = os.path.join(DATA_DIR, "blockchain_ledger.json")
USERS_CSV     = os.path.join(DATA_DIR, "users.csv")
METRICS_PATH  = os.path.join(MODELS_DIR, "forecast_metrics.json")
MODEL_PATH    = os.path.join(MODELS_DIR, "forecast_prophet.joblib")
