"""
BloxLogicAI — tea export volume forecasting (Prophet).

Two interchangeable models share one pipeline, selected at the command line:

    python models/forecasting.py --model univariate
    python models/forecasting.py --model multivariate

* **Univariate** learns trend, yearly seasonality and the 2022 economic-crisis
  shock from export history alone (data/processed/forecast_univariant.csv: ds, y MT).
* **Multivariate** adds production, USD/LKR and tea-region weather as Prophet
  regressors (data/processed/forecast_multivariant.csv). Future driver values are
  cascade-forecast (each driver projected by its own Prophet) so the model can
  predict ahead without leaking held-out data.

Shared, model-agnostic primitives (used by both, by tests and by the dashboard):
    load_forecast_data() / load_multivariate_data()  -> tidy DataFrame
    train_model(df, regressors=())                    -> fitted Prophet
    predict(model, periods)                           -> forecast DataFrame
    evaluate(df, test_periods, regressors=())         -> {mae, rmse, mape, ...}
    save_model / load_model                           -> joblib persistence

High-level orchestrators (backtest -> train-on-all -> persist -> forecast):
    run_univariate_model(df)
    run_multivariate_model(df)
"""

from __future__ import annotations

import os
import json
import argparse
import numpy as np
import pandas as pd
import joblib
from prophet import Prophet

# ---------------------------------------------------------------------------
# Paths & configuration
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
SAVED = os.path.join(ROOT, "models", "saved")

# Univariate dataset/artefacts. NOTE: DATA/MODEL_PATH/METRICS_PATH keep their
# original names because the Streamlit app and tests import them directly.
DATA = os.path.join(PROCESSED, "forecast_univariant.csv")
MODEL_PATH = os.path.join(SAVED, "forecast_prophet.joblib")
METRICS_PATH = os.path.join(SAVED, "forecast_metrics.json")

# Multivariate dataset/artefacts (kept separate so neither model overwrites the other).
MV_DATA = os.path.join(PROCESSED, "forecast_multivariant.csv")
MV_MODEL_PATH = os.path.join(SAVED, "forecast_prophet_mv.joblib")
MV_METRICS_PATH = os.path.join(SAVED, "forecast_metrics_mv.json")

# The additive drivers for the multivariate model (must exist as columns in MV_DATA).
MV_REGRESSORS = ["production_mt", "usd_lkr_avg", "rainfall_mm", "temp_mean"]
REGRESSOR_MODE = "additive"

FORECAST_HORIZON = 12   # months to project ahead
TEST_PERIODS = 12       # hold-out length for the backtest

# Sensible defaults for a monthly volume series ~14 years long. Shared by both models.
DEFAULT_PARAMS = dict(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    seasonality_mode="multiplicative",
    changepoint_prior_scale=0.5,   # allow the 2022 crisis trend break
    interval_width=0.90,
)


# ---------------------------------------------------------------------------
# Shared preprocessing  (kept OUTSIDE the model runners — DRY)
# ---------------------------------------------------------------------------
def _prepare(df: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    """Common cleaning both models need: parse ds, drop incomplete rows, sort.

    `required` is the set of columns that must be present (target and any
    regressors); rows missing any of them are dropped so Prophet never sees NaN.
    """
    df = df.copy()
    df["ds"] = pd.to_datetime(df["ds"])
    return (df.dropna(subset=required)
              .sort_values("ds")
              .reset_index(drop=True))


def load_forecast_data(path: str = DATA) -> pd.DataFrame:
    """Load the univariate forecast dataset as a clean (ds, y) series."""
    df = pd.read_csv(path, parse_dates=["ds"])
    return _prepare(df, ["y"])[["ds", "y"]]


def load_multivariate_data(path: str = MV_DATA,
                           regressors: list[str] = MV_REGRESSORS) -> pd.DataFrame:
    """Load the multivariate dataset as a clean (ds, y, *regressors) frame."""
    df = pd.read_csv(path, parse_dates=["ds"])
    cols = ["y"] + list(regressors)
    return _prepare(df, cols)[["ds"] + cols]


# ---------------------------------------------------------------------------
# Train / predict primitives  (shared; regressors optional)
# ---------------------------------------------------------------------------
def train_model(df: pd.DataFrame, regressors: tuple | list = (), **params) -> Prophet:
    """Fit Prophet on a (ds, y[, *regressors]) frame.

    With no regressors this is the univariate model. Pass `regressors` to add
    them as additive predictors for the multivariate model.
    """
    regressors = list(regressors)
    cfg = {**DEFAULT_PARAMS, **params}
    model = Prophet(**cfg)
    for r in regressors:
        model.add_regressor(r, mode=REGRESSOR_MODE)
    model.fit(df[["ds", "y"] + regressors])
    return model


def predict(model: Prophet, periods: int = FORECAST_HORIZON,
            freq: str = "MS") -> pd.DataFrame:
    """Univariate forecast `periods` ahead; returns ds + yhat (+ bounds).

    For the multivariate model use `predict_multivariate`, which also supplies
    the required future regressor values.
    """
    future = model.make_future_dataframe(periods=periods, freq=freq)
    fc = model.predict(future)
    return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]]


# ---------------------------------------------------------------------------
# Future drivers for the multivariate model (cascade forecast + what-if)
# ---------------------------------------------------------------------------
def forecast_regressor(history: pd.DataFrame, col: str,
                       future_ds) -> np.ndarray:
    """Project one driver onto `future_ds` with its own lightweight Prophet."""
    series = history[["ds", col]].rename(columns={col: "y"}).dropna()
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                    daily_seasonality=False)
    model.fit(series)
    fc = model.predict(pd.DataFrame({"ds": list(future_ds)}))
    return fc["yhat"].to_numpy()


def make_future_regressors(history: pd.DataFrame, regressors: list[str],
                           periods: int = FORECAST_HORIZON, freq: str = "MS",
                           overrides: dict | None = None) -> pd.DataFrame:
    """Build a future (ds, *regressors) frame by cascade-forecasting each driver.

    `overrides` lets a caller force a driver to a fixed value (the dashboard's
    "what-if" scenarios, e.g. {"usd_lkr_avg": 400.0}). A callable override
    receives the auto-estimated series and returns the adjusted one (e.g. a 10%
    production drop: {"production_mt": lambda s: s * 0.90}).
    """
    last = history["ds"].max()
    future_ds = pd.date_range(last + pd.offsets.MonthBegin(1), periods=periods, freq=freq)
    future = pd.DataFrame({"ds": future_ds})
    for r in regressors:
        future[r] = forecast_regressor(history, r, future_ds)

    for col, val in (overrides or {}).items():
        future[col] = val(future[col]) if callable(val) else val
    return future


def predict_multivariate(model: Prophet, history: pd.DataFrame,
                         regressors: list[str] = MV_REGRESSORS,
                         periods: int = FORECAST_HORIZON, freq: str = "MS",
                         future_regressors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Multivariate forecast: combine history with future driver values, then predict.

    If `future_regressors` is omitted the drivers are cascade-forecast. Returns
    the full history+future frame with ds + yhat (+ bounds), mirroring `predict`.
    """
    regressors = list(regressors)
    if future_regressors is None:
        future_regressors = make_future_regressors(history, regressors, periods, freq)
    frame = pd.concat(
        [history[["ds"] + regressors], future_regressors[["ds"] + regressors]],
        ignore_index=True,
    )
    fc = model.predict(frame)
    return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]]


# ---------------------------------------------------------------------------
# Evaluate (hold-out backtest; shared by both models)
# ---------------------------------------------------------------------------
def _score(actual: np.ndarray, pred: np.ndarray) -> dict:
    """MAE / RMSE / MAPE for an actual-vs-predicted pair."""
    err = actual - pred
    return {
        "mae": round(float(np.mean(np.abs(err))), 2),
        "rmse": round(float(np.sqrt(np.mean(err ** 2))), 2),
        "mape": round(float(np.mean(np.abs(err / actual)) * 100), 2),
    }


def evaluate(df: pd.DataFrame, test_periods: int = TEST_PERIODS,
             regressors: tuple | list = (), future: str = "forecast",
             **params) -> dict:
    """Hold out the last `test_periods` months, fit on the rest, score them.

    Univariate when `regressors` is empty. For the multivariate model `future`
    controls how the held-out driver values are obtained:
      * "forecast" (default) — cascade-forecast the drivers from the TRAIN split
        only; the honest, operational metric (no leakage).
      * "actual" — use the real held-out drivers; an oracle upper bound.
    """
    regressors = list(regressors)
    if len(df) <= test_periods:
        raise ValueError("Not enough history for the requested hold-out.")

    train, test = df.iloc[:-test_periods], df.iloc[-test_periods:]
    model = train_model(train, regressors, **params)

    if not regressors:
        fc = predict(model, periods=test_periods).set_index("ds")
        pred = fc.loc[test["ds"], "yhat"].to_numpy()
    else:
        if future == "forecast":
            fut = test[["ds"]].copy()
            for r in regressors:
                fut[r] = forecast_regressor(train, r, test["ds"])
        elif future == "actual":
            fut = test[["ds"] + regressors].copy()
        else:
            raise ValueError("future must be 'forecast' or 'actual'")
        frame = pd.concat([train[["ds"] + regressors], fut[["ds"] + regressors]],
                          ignore_index=True)
        pred = model.predict(frame).set_index("ds").reindex(test["ds"])["yhat"].to_numpy()

    metrics = {
        "model": "multivariate" if regressors else "univariate",
        "test_periods": int(test_periods),
        **_score(test["y"].to_numpy(), pred),
        "train_start": str(train["ds"].min().date()),
        "test_start": str(test["ds"].min().date()),
        "test_end": str(test["ds"].max().date()),
    }
    if regressors:
        metrics["regressors"] = regressors
        metrics["future_drivers"] = future
    return metrics


# ---------------------------------------------------------------------------
# Persistence (shared)
# ---------------------------------------------------------------------------
def save_model(model: Prophet, path: str = MODEL_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    return path


def load_model(path: str = MODEL_PATH) -> Prophet:
    return joblib.load(path)


def _save_metrics(metrics: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(metrics, fh, indent=2)


# ---------------------------------------------------------------------------
# Model runners (orchestration: backtest -> train on all -> persist -> forecast)
# ---------------------------------------------------------------------------
def run_univariate_model(df: pd.DataFrame, *, horizon: int = FORECAST_HORIZON,
                         test_periods: int = TEST_PERIODS, save: bool = True) -> dict:
    """Train, backtest and forecast the univariate export-volume model."""
    metrics = evaluate(df, test_periods=test_periods)
    model = train_model(df)
    forecast = predict(model, periods=horizon)
    if save:
        save_model(model, MODEL_PATH)
        _save_metrics(metrics, METRICS_PATH)
    return {"model": model, "metrics": metrics, "forecast": forecast,
            "model_path": MODEL_PATH, "metrics_path": METRICS_PATH}


def run_multivariate_model(df: pd.DataFrame, *, regressors: list[str] = MV_REGRESSORS,
                           horizon: int = FORECAST_HORIZON, test_periods: int = TEST_PERIODS,
                           future: str = "forecast", save: bool = True) -> dict:
    """Train, backtest and forecast the multivariate (driver-aware) model."""
    regressors = list(regressors)
    metrics = evaluate(df, test_periods=test_periods, regressors=regressors, future=future)
    model = train_model(df, regressors)
    forecast = predict_multivariate(model, df, regressors, periods=horizon)
    if save:
        save_model(model, MV_MODEL_PATH)
        _save_metrics(metrics, MV_METRICS_PATH)
    return {"model": model, "metrics": metrics, "forecast": forecast,
            "model_path": MV_MODEL_PATH, "metrics_path": MV_METRICS_PATH}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _report(kind: str, df: pd.DataFrame, result: dict, horizon: int) -> None:
    """Print a consistent summary for either model."""
    print(f"=== {kind.upper()} Prophet model ===")
    print(f"Loaded {len(df)} months: {df.ds.min():%Y-%m} -> {df.ds.max():%Y-%m}")
    print("Backtest:")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")

    print(f"\nNext {horizon}-month forecast (MT):")
    print(result["forecast"].tail(horizon).assign(
        yhat=lambda d: d.yhat.round(0),
        yhat_lower=lambda d: d.yhat_lower.round(0),
        yhat_upper=lambda d: d.yhat_upper.round(0),
    ).to_string(index=False))
    print(f"\nSaved model   -> {result['model_path']}")
    print(f"Saved metrics -> {result['metrics_path']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Train, backtest and forecast tea export volume with Prophet.")
    parser.add_argument("--model", choices=["univariate", "multivariate"],
                        default="univariate",
                        help="which model to run (default: univariate)")
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON,
                        help="months to forecast ahead (default: 12)")
    parser.add_argument("--test-periods", type=int, default=TEST_PERIODS,
                        help="hold-out length for the backtest (default: 12)")
    parser.add_argument("--future", choices=["forecast", "actual"], default="forecast",
                        help="multivariate only: how held-out drivers are obtained "
                             "(default: forecast)")
    parser.add_argument("--no-save", action="store_true",
                        help="run without writing model/metrics artefacts")
    args = parser.parse_args(argv)

    # Shared dispatch: load the right dataset, then run the chosen model.
    if args.model == "univariate":
        df = load_forecast_data()
        result = run_univariate_model(df, horizon=args.horizon,
                                      test_periods=args.test_periods,
                                      save=not args.no_save)
    else:
        df = load_multivariate_data()
        result = run_multivariate_model(df, horizon=args.horizon,
                                        test_periods=args.test_periods,
                                        future=args.future, save=not args.no_save)

    _report(args.model, df, result, args.horizon)


if __name__ == "__main__":
    main()
