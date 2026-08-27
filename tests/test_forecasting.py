"""Tests for the Prophet forecasting module (models/forecasting.py)."""

import numpy as np
import pandas as pd
import pytest
from prophet import Prophet

from models import forecasting as fc


@pytest.fixture(scope="module")
def sample_df():
    """A 48-month synthetic series with trend + yearly seasonality."""
    ds = pd.date_range("2018-01-01", periods=48, freq="MS")
    t = np.arange(48)
    y = 20000 + 30 * t + 1500 * np.sin(2 * np.pi * t / 12) + 200 * np.random.RandomState(0).randn(48)
    return pd.DataFrame({"ds": ds, "y": y})


@pytest.fixture(scope="module")
def trained_model(sample_df):
    return fc.train_model(sample_df)


def test_train_returns_model(trained_model):
    assert isinstance(trained_model, Prophet)


def test_predict_returns_dataframe(trained_model):
    out = fc.predict(trained_model, periods=6)
    assert isinstance(out, pd.DataFrame)
    assert {"ds", "yhat", "yhat_lower", "yhat_upper"} <= set(out.columns)
    # history (48) + 6 future rows
    assert len(out) == 48 + 6
    assert out["yhat"].notna().all()


def test_evaluate_returns_metrics(sample_df):
    m = fc.evaluate(sample_df, test_periods=6)
    for key in ("mae", "rmse", "mape", "test_periods"):
        assert key in m
    assert m["mae"] >= 0 and m["rmse"] >= 0
    # synthetic series is smooth -> error should be modest
    assert m["mape"] < 25


def test_save_and_load_model(trained_model, tmp_path):
    path = tmp_path / "m.joblib"
    fc.save_model(trained_model, str(path))
    assert path.exists()
    loaded = fc.load_model(str(path))
    out = fc.predict(loaded, periods=3)
    assert len(out) == 48 + 3


def test_load_forecast_data_real():
    """The real processed dataset loads as a clean (ds, y) series."""
    df = fc.load_forecast_data()
    assert list(df.columns) == ["ds", "y"]
    assert len(df) > 100                     # long history
    assert df["y"].notna().all()
    assert df["ds"].is_monotonic_increasing
