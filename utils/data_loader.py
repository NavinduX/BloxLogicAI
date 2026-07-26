"""
BloxLogicAI — data loading & preprocessing pipeline.

Builds a single monthly master dataset from real source data, then emits two
model-specific views:
  - forecast_dataset.csv  (Prophet: long target history, lean regressors)
  - anomaly_dataset.csv   (Isolation Forest: feature-rich, real months only)

Real sources (data/sources/):
  - monthly_tea_raw.csv ........ monthly production/export hand-extracted from
                                 SLTB Monthly Tea Statistics PDFs (Aug21-Oct23)
  - USDtoLKR.csv ............... daily USD/LKR indicative rate (2019-2026)
  - climate/SriLanka_Weather_Dataset.csv .. daily weather, 30 cities (2010-2023)
"""

from __future__ import annotations

import os
import glob
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SOURCES = os.path.join(ROOT, "data", "sources")
PROCESSED = os.path.join(ROOT, "data", "processed")

TEA_RAW = os.path.join(RAW, "monthly_tea_raw.csv")
USD_CSV = os.path.join(SOURCES, "usd_lkr_historical.csv")
WEATHER_DIR = os.path.join(SOURCES, "sri_lanka_weather_data")
EXPORT_CSV = os.path.join(SOURCES, "Export_Data_2011_to_2026.csv")
PRODUCTION_CSV = os.path.join(SOURCES, "Production_Data_2011_to_2026.csv")

# Tea-growing districts -> elevation zone (matches the High/Medium/Low production split).
# The per-district weather files include Nuwara Eliya & Badulla (high-grown); dry-zone /
# non-tea districts (Hambantota, Jaffna, Colombo, etc.) are deliberately excluded so the
# climate signal reflects where tea is actually grown.
TEA_DISTRICT_ZONES = {
    "Nuwara Eliya": "High", "Badulla": "High",
    "Kandy": "Medium", "Matale": "Medium",
    "Ratnapura": "Low", "Kegalle": "Low", "Galle": "Low",
    "Matara": "Low", "Kalutara": "Low",
}

# Official SLTB annual export totals (MT) — used to derive 2022-12 and validate.
ANNUAL_EXPORT_MT = {2021: 286016, 2022: 250191, 2023: 241912}


# ---------------------------------------------------------------------------
# Export: long monthly history (2011-2026) -> single national total series
# ---------------------------------------------------------------------------
def load_export_monthly() -> pd.DataFrame:
    """National monthly tea export volume (MT) from the SLTB customs export file.

    The file is a hierarchical dump: detail rows per category/package plus
    embedded 'Sub Total' / 'Total Exports' / 'Grand Total' lines whose labels
    drift across years. The clean per-month total is the 'Total Exports' line;
    where both a plain and a '(Without RTD)' variant exist we keep Without-RTD
    (RTD is a tiny liquid product reported in litres, not comparable kg).
    Quantities are in kg; converted to MT ('000 kg) to match official totals.
    """
    df = pd.read_csv(EXPORT_CSV, usecols=range(6),
                     names=["month", "category", "pkg", "qty_kg", "price", "mrec"],
                     header=0)
    df["month"] = pd.to_datetime(df["month"].fillna(df["mrec"]), errors="coerce")
    df["qty_kg"] = pd.to_numeric(df["qty_kg"], errors="coerce")

    tot = df[df["pkg"].astype(str).str.contains("Total Exports", na=False)].copy()
    tot = tot.dropna(subset=["month", "qty_kg"])
    tot["without_rtd"] = tot["pkg"].astype(str).str.contains("Without RTD", na=False)

    # one row per month: prefer the Without-RTD total when present
    tot = (tot.sort_values(["month", "without_rtd"])  # False then True
              .groupby("month", as_index=False).last())
    out = tot[["month", "qty_kg"]].copy()
    out["export_mt"] = out["qty_kg"] / 1000.0
    return out[["month", "export_mt"]].sort_values("month").reset_index(drop=True)


def load_production_monthly() -> pd.DataFrame:
    """National monthly tea production (MT) from the elevation 'Total' rows."""
    df = pd.read_csv(PRODUCTION_CSV, usecols=range(4),
                     names=["month", "elev", "qty_kg", "mrec"], header=0)
    df["month"] = pd.to_datetime(df["month"].fillna(df["mrec"]), errors="coerce")
    df["qty_kg"] = pd.to_numeric(df["qty_kg"], errors="coerce")
    tot = df[df["elev"].astype(str).str.strip().eq("Total")].dropna(
        subset=["month", "qty_kg"])
    out = tot.groupby("month", as_index=False)["qty_kg"].sum()
    out["production_mt"] = out["qty_kg"] / 1000.0
    return out[["month", "production_mt"]].sort_values("month").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Macro: USD/LKR daily -> monthly
# ---------------------------------------------------------------------------
def load_macro_monthly() -> pd.DataFrame:
    """Monthly USD/LKR: mean rate + intra-month volatility (std of daily close).

    Source: usd_lkr_historical.csv - a Yahoo `LKR=X` daily export (2011-2026) with two
    metadata rows under the header; the date sits in the 'Price' column, the rate in 'Close'.
    """
    df = pd.read_csv(USD_CSV, skiprows=[1, 2])
    df = df.rename(columns={"Price": "date", "Close": "rate"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df = df.dropna(subset=["date", "rate"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    out = (
        df.groupby("month")["rate"]
        .agg(usd_lkr_avg="mean", usd_lkr_volatility="std")
        .reset_index()
    )
    return out


# ---------------------------------------------------------------------------
# Production by elevation zone (used to weight the tea-region weather)
# ---------------------------------------------------------------------------
def load_production_by_zone() -> pd.DataFrame:
    """Monthly tea production (MT) split by elevation zone: High / Medium / Low."""
    df = pd.read_csv(PRODUCTION_CSV, usecols=range(4),
                     names=["month", "elev", "qty_kg", "mrec"], header=0)
    df["month"] = pd.to_datetime(df["month"].fillna(df["mrec"]), errors="coerce")
    df["qty_kg"] = pd.to_numeric(df["qty_kg"], errors="coerce")
    df["elev"] = df["elev"].astype(str).str.strip()
    df = df[df["elev"].isin(["High", "Medium", "Low"])].dropna(subset=["month", "qty_kg"])
    wide = (df.groupby(["month", "elev"])["qty_kg"].sum().unstack("elev") / 1000.0)
    wide = wide.reindex(columns=["High", "Medium", "Low"])
    wide.columns = ["prod_high", "prod_medium", "prod_low"]
    return wide.reset_index()


def _prod_weighted(zone_df: pd.DataFrame, shares: pd.DataFrame) -> pd.Series:
    """Combine per-zone monthly weather into one national series, weighted by production share.

    Months/zones lacking weather fall back to equal weights; weights are renormalised so the
    national value always averages whatever zones are present.
    """
    cols = [c for c in ["High", "Medium", "Low"] if c in zone_df.columns]
    zone_df = zone_df[cols]
    w = shares.reindex(zone_df.index).reindex(columns=cols)
    w = w.fillna(pd.DataFrame(1.0, index=zone_df.index, columns=cols))
    w = w.where(zone_df.notna())
    w = w.div(w.sum(axis=1), axis=0)
    return (zone_df * w).sum(axis=1, min_count=1)


# ---------------------------------------------------------------------------
# Climate: per-district daily weather -> production-weighted tea-region monthly
# ---------------------------------------------------------------------------
def load_weather_monthly() -> pd.DataFrame:
    """National monthly tea-region climate: rainfall (mm) and mean temperature (C).

    Reads the per-district daily files in data/sources/sri_lanka_weather_data/ (2011-2026),
    keeps only the tea-growing districts (TEA_DISTRICT_ZONES), aggregates to monthly per
    elevation zone, then combines the zones weighted by each month's share of national
    production so the biggest-producing elevations dominate. Dry-zone / non-tea districts are
    excluded so the signal reflects where tea is actually grown.
    """
    files = sorted(glob.glob(os.path.join(WEATHER_DIR, "*.csv")))
    raw = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    raw = raw[raw["district"].isin(TEA_DISTRICT_ZONES)].copy()
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw.dropna(subset=["date"])
    raw["rain"] = pd.to_numeric(raw["rain_sum"], errors="coerce")
    raw["temp"] = (pd.to_numeric(raw["temperature_2m_max"], errors="coerce")
                   + pd.to_numeric(raw["temperature_2m_min"], errors="coerce")) / 2.0
    raw["zone"] = raw["district"].map(TEA_DISTRICT_ZONES)
    raw["month"] = raw["date"].dt.to_period("M").dt.to_timestamp()

    # per district-month: total rain, mean temp -> per zone-month: mean across districts
    dm = (raw.groupby(["zone", "district", "month"])
             .agg(rain=("rain", "sum"), temp=("temp", "mean")).reset_index())
    zm = (dm.groupby(["zone", "month"])
             .agg(rain=("rain", "mean"), temp=("temp", "mean")).reset_index())
    rain_z = zm.pivot(index="month", columns="zone", values="rain")
    temp_z = zm.pivot(index="month", columns="zone", values="temp")

    # production-share weights per month
    shares = load_production_by_zone().set_index("month")[["prod_high", "prod_medium", "prod_low"]]
    shares.columns = ["High", "Medium", "Low"]
    shares = shares.div(shares.sum(axis=1), axis=0)

    return pd.DataFrame({
        "month": rain_z.index,
        "rainfall_mm": _prod_weighted(rain_z, shares).values,
        "temp_mean": _prod_weighted(temp_z, shares).values,
    })


# ---------------------------------------------------------------------------
# Tea: hand-extracted monthly raw
# ---------------------------------------------------------------------------
def load_tea_monthly() -> pd.DataFrame:
    """Load monthly tea production/export; clean known cumulative-format rows."""
    df = pd.read_csv(TEA_RAW)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["month"])

    # 2021-08 PDF reports CUMULATIVE (Jan-Aug) exports, not a single month.
    # Keep its production (valid single-month); drop its export/value/fob.
    aug21 = df["month"] == pd.Timestamp("2021-08-01")
    df.loc[aug21, ["export_mt", "export_value_lkr_mn", "fob_rs_kg"]] = pd.NA

    # 2022-12 export missing from source; derive from official annual total.
    known_2022 = df[(df.month.dt.year == 2022) & df.export_mt.notna()]["export_mt"].sum()
    dec22 = df["month"] == pd.Timestamp("2022-12-01")
    df.loc[dec22, "export_mt"] = ANNUAL_EXPORT_MT[2022] - known_2022

    # mark which export points are derived rather than read from a report
    df["export_derived"] = dec22
    return df


# ---------------------------------------------------------------------------
# Merge -> single monthly master
# ---------------------------------------------------------------------------
def build_master() -> pd.DataFrame:
    """Left-join tea (the spine) with macro + weather on month."""
    tea = load_tea_monthly()
    macro = load_macro_monthly()
    weather = load_weather_monthly()

    master = (
        tea.merge(macro, on="month", how="left")
        .merge(weather, on="month", how="left")
        .sort_values("month")
        .reset_index(drop=True)
    )
    return master


# ---------------------------------------------------------------------------
# View 1 — Prophet forecast dataset
# ---------------------------------------------------------------------------
def build_forecast_dataset() -> pd.DataFrame:
    """Continuous monthly univariate series for Prophet (ds, y = export MT).

    Source: the long 2011-2026 customs export file (~166 real monthly points),
    which gives Prophet enough history to learn yearly seasonality, trend and
    the 2022 economic-crisis shock. A handful of months are missing from the
    file; we reindex to a continuous monthly spine and time-interpolate those
    gaps, flagging every imputed point in `y_imputed` for honest reporting.
    """
    exp = load_export_monthly()

    # continuous monthly spine across the real coverage
    full = pd.date_range(exp["month"].min(), exp["month"].max(), freq="MS")
    fc = exp.set_index("month").reindex(full)
    fc.index.name = "ds"
    fc = fc.reset_index()

    fc["y_imputed"] = fc["export_mt"].isna()
    fc = fc.set_index("ds")
    fc["export_mt"] = fc["export_mt"].interpolate(method="time",
                                                  limit_direction="both")
    fc = fc.reset_index().rename(columns={"export_mt": "y"})
    return fc[["ds", "y", "y_imputed"]]


# ---------------------------------------------------------------------------
# View 1b — multivariate forecast dataset (Prophet with regressors)
# ---------------------------------------------------------------------------
MV_REGRESSORS = ["production_mt", "usd_lkr_avg", "rainfall_mm", "temp_mean"]


def build_multivariate_dataset() -> pd.DataFrame:
    """Continuous monthly frame for Prophet-with-regressors.

    Columns: ds, y (export MT) + the driver regressors (production, USD/LKR, tea-region
    rainfall & temperature), each on a continuous monthly spine over the export coverage.
    Small internal gaps are time-interpolated per column and flagged in `<col>_imputed`.
    With all drivers now spanning 2011-2026 the frame is gap-free apart from a few
    export / production months.
    """
    exp = load_export_monthly().rename(columns={"month": "ds", "export_mt": "y"})
    prod = load_production_monthly().rename(columns={"month": "ds"})
    macro = load_macro_monthly()[["month", "usd_lkr_avg"]].rename(columns={"month": "ds"})
    weather = load_weather_monthly().rename(columns={"month": "ds"})

    spine = pd.date_range(exp["ds"].min(), exp["ds"].max(), freq="MS")
    df = (pd.DataFrame({"ds": spine})
          .merge(exp, on="ds", how="left")
          .merge(prod, on="ds", how="left")
          .merge(macro, on="ds", how="left")
          .merge(weather, on="ds", how="left")
          .set_index("ds"))

    for col in ["y"] + MV_REGRESSORS:
        df[f"{col}_imputed"] = df[col].isna()
        df[col] = df[col].interpolate(method="time", limit_direction="both")
    df = df.reset_index()

    keep = ["ds", "y", "y_imputed"] + MV_REGRESSORS + [f"{c}_imputed" for c in MV_REGRESSORS]
    return df[keep]


# ---------------------------------------------------------------------------
# View 2 — Isolation Forest anomaly dataset
# ---------------------------------------------------------------------------
def build_anomaly_dataset(master: pd.DataFrame | None = None) -> pd.DataFrame:
    """Feature-rich, real-months-only view for Isolation Forest.

    Keeps only months with a genuine (reported or annual-derived) export value
    and a full feature row — no target interpolation, because injecting smooth
    synthetic points would mask the very anomalies the model must find.
    """
    if master is None:
        master = build_master()

    feature_cols = ["production_mt", "export_mt", "export_value_lkr_mn",
                    "fob_rs_kg", "usd_lkr_avg", "usd_lkr_volatility",
                    "rainfall_mm", "temp_mean"]
    an = master[["month"] + feature_cols + ["export_derived"]].copy()

    # Isolation Forest cannot take NaN; require every feature present. This also
    # excludes the derived Dec-2022 row (no reported fob_rs_kg), keeping the
    # anomaly set to 100% reported signals.
    an = an.dropna(subset=feature_cols).reset_index(drop=True)
    return an


def _summ(df: pd.DataFrame, cols) -> str:
    nn = df[cols].notna().sum().to_dict()
    return f"{len(df)} rows; non-null {nn}"


if __name__ == "__main__":
    os.makedirs(PROCESSED, exist_ok=True)

    # View 1 - univariate forecast dataset (unchanged; keeps the current app working)
    fc = build_forecast_dataset()
    fc.to_csv(os.path.join(PROCESSED, "forecast_dataset.csv"), index=False)
    print("=== FORECAST (Prophet, univariate export volume) ===")
    print(_summ(fc, ["y"]))
    print(f"range {fc.ds.min():%Y-%m} -> {fc.ds.max():%Y-%m}; imputed y: {int(fc.y_imputed.sum())}")
    yr = fc.assign(year=fc.ds.dt.year).groupby("year")["y"].sum().round(0)
    print("annual export (MT):", {int(k): int(v) for k, v in yr.items()})

    # View 1b - multivariate forecast dataset (ds, y + production/FX/weather regressors)
    mv = build_multivariate_dataset()
    mv.to_csv(os.path.join(PROCESSED, "forecast_multivariate.csv"), index=False)
    print("\n=== MULTIVARIATE (Prophet + regressors) ===")
    print(_summ(mv, ["y"] + MV_REGRESSORS))
    print(f"range {mv.ds.min():%Y-%m} -> {mv.ds.max():%Y-%m}; "
          f"imputed production: {int(mv.production_mt_imputed.sum())}")

    # Processed driver series (committed so the repo reproduces without the raw sources)
    prod = load_production_monthly().merge(load_production_by_zone(), on="month", how="left")
    prod.to_csv(os.path.join(PROCESSED, "production_monthly.csv"), index=False)
    load_macro_monthly().to_csv(os.path.join(PROCESSED, "fx_monthly.csv"), index=False)
    load_weather_monthly().to_csv(os.path.join(PROCESSED, "weather_tea_monthly.csv"), index=False)

    print("\nWrote -> data/processed/: forecast_dataset.csv, forecast_multivariate.csv, "
          "production_monthly.csv, fx_monthly.csv, weather_tea_monthly.csv")
