# CLAUDE.md — BloxLogicAI

Project-level guidance for Claude Code. Read this first. It overrides assumptions; if it conflicts with the code, trust the code and flag the drift.

---

## 1. What this is

**BloxLogicAI** — *An AI and Blockchain-Enabled Supply Chain Forecasting & Analysis System for Sri Lanka's Tea Industry.*

This is a **BSc (Hons) Software Engineering final-year dissertation** project.

- **Student ID:** CL/BSCSD/33/160
- **Awarding body:** Cardiff Metropolitan University (via ICBT)
- **Submission deadline:** 2026-06-29 (hard)
- **Proposal of record:** `FINAL_PROJECT_PROPOSAL_33_160.pdf`

It is a single, lightweight, Python web app (Streamlit) — **no database, no cloud services**. Storage is flat files (CSV/JSON). It must run locally with `streamlit run app/main.py`.

---

## 2. The three modules (deliverables)

| # | Module | Tech | Status |
|---|--------|------|--------|
| 1 | **Forecasting** — monthly tea export volume | Facebook Prophet (univariate) | ✅ Done + tested |
| 2 | **Anomaly detection** — flag supply-chain disruptions | scikit-learn Isolation Forest | ⏳ Next (deferred by user until forecasting fully reviewed) |
| 3 | **Blockchain traceability** — immutable tea-batch ledger | Python SHA-256 hash chain | 🔲 Not started |

A Streamlit dashboard ties all three together (User Portal + Admin Portal in the proposal; currently a single forecasting dashboard).

**Build order is fixed:** finish and test one module fully (implement → test → fix → commit) before starting the next. The user explicitly wants Prophet completely done and reviewed before anomaly detection.

---

## 3. Tech stack & environment

- **Python 3.10+**. Pinned deps in `requirements.txt`.
- **Always use the project venv:** `.venv/Scripts/python.exe` — **not** the global `Python310`.
- UI: Streamlit 1.35 · Forecasting: Prophet 1.1.5 · Anomaly: scikit-learn 1.5 · Data: pandas/numpy · Charts: Plotly · Persistence: joblib + JSON.

### Environment gotcha (important)
Prophet 1.1.5 ships a **stripped cmdstan** (no makefile). cmdstanpy 1.3.x rejects it with `CmdStan installation missing makefile ... is invalid`. **Pinned fix:** `cmdstanpy==1.2.4` (laxer validation). This is already in `requirements.txt` — do not bump it.

### Common commands
```bash
# run the dashboard (from project root)
.venv/Scripts/python.exe -m streamlit run app/main.py

# run tests
.venv/Scripts/python.exe -m pytest tests/ -v

# rebuild the processed forecast dataset from sources
.venv/Scripts/python.exe utils/data_loader.py

# retrain + backtest the Prophet model
.venv/Scripts/python.exe models/forecasting.py
```

---

## 4. Repository layout

```
BloxLogicAI/
├── app/main.py              # Streamlit dashboard (forecasting; entry point)
├── models/
│   ├── forecasting.py       # Prophet: train/predict/evaluate/save/load + main()
│   └── saved/               # forecast_prophet.joblib + forecast_metrics.json (committed)
├── blockchain/              # SHA-256 ledger (to build)
├── utils/data_loader.py     # central data pipeline → model-specific datasets
├── data/
│   ├── sources/             # raw third-party source CSVs — GITIGNORED (large)
│   ├── raw/                 # extracted raw (committed)
│   └── processed/           # forecast_dataset.csv etc. (committed)
├── tests/test_forecasting.py
├── docs/                    # diagrams, REQUIREMENTS.md, user manual
├── requirements.txt
├── README.md
└── CLAUDE.md                # this file
```

---

## 5. Data pipeline (`utils/data_loader.py`)

One builder produces **model-specific views**. Do not let models read source files directly.

### Sources (in `data/sources/`, gitignored)
- `Export_Data_2011_to_2026.csv` — hierarchical monthly SLTB customs dump. **Use the `Total Exports (Without RTD)` line per month** (prefer the Without-RTD variant) as the national total. `qty` is in **kg → ÷1000 = MT**. Yields ~166–175 clean months; reconciles to official annual totals within ~1–5%.
- `Production_Data_2011_to_2026.csv` — monthly by elevation; use `Total` rows. Good 2012–2021, partial after.
- `USDtoLKR.csv` (monthly 2019–2026) + weather climate CSV (monthly 2019–2023) — **anomaly features only**.
- `Sales_Data_2011_to_2026.csv` — too sparse, **dropped**.
- `SL_Tea_Export.csv` / `SL_Tea_Production.csv` — annual cross-check only.

### Forecast dataset (the one in use)
`build_forecast_dataset()` → `data/processed/forecast_dataset.csv`:
- **Univariate**: columns `ds`, `y` (export MT), plus `y_imputed` flag.
- Reindexed to a continuous monthly spine (`freq="MS"`); ~5 missing months are time-interpolated and flagged `y_imputed=True`.
- ~175 monthly points spanning **2011-10 → 2026-04**.

### Anomaly builders (present, for module 2)
`build_master()` / `build_anomaly_dataset()` exist but are deferred. Plan: richer feature window **2019–2023** (export, production, USD/LKR, weather), `dropna` on feature columns (~21 clean rows), exclude derived/imputed rows.

---

## 6. Forecasting module (`models/forecasting.py`) — DONE

- **Univariate Prophet.** `DEFAULT_PARAMS`: `yearly_seasonality=True`, `weekly`/`daily=False`, `seasonality_mode="multiplicative"`, `changepoint_prior_scale=0.5` (captures the 2022 economic-crisis trend break), `interval_width=0.90`.
- **API:** `load_forecast_data()`, `train_model(df, **params)`, `predict(model, periods=12, freq="MS")` (returns history+future with `ds/yhat/yhat_lower/yhat_upper`), `evaluate(df, test_periods=12)`, `save_model`/`load_model` (joblib), `main()`.
- **Backtest (last 12 months hold-out):** MAPE **9.06%**, MAE **~1768 MT**, RMSE ~1977. Stored in `models/saved/forecast_metrics.json`.
- **Tests:** `tests/test_forecasting.py` — 5 passing (train, predict shape, evaluate metrics with `mape<25`, save/load round-trip, real-dataset load).

---

## 7. Conventions & workflow

- **Git commits** must end with the trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Commit / push only when the user asks.** Branch off `main` is the working branch; remote `origin` = `https://github.com/nalantishantha/BloxLogicAI.git`.
- **.gitignore policy (user decision):** ignore **only** `data/sources/` (large third-party data), `models/saved/*.pkl`, and `data/users.csv` (runtime credential store — holds password hashes, must not be committed). Everything else — including `data/raw/`, `data/processed/`, the joblib model, and `*_metrics.json` — **is committed** so the project is reproducible for the examiner.
- Match the existing code style (type hints, `from __future__ import annotations`, concise docstrings, section banner comments).
- The user's global config mandates prefixing shell commands with `rtk` (a safe token-optimizing passthrough wrapper).
- Keep changes scoped to the current module; don't pre-build later modules.

---

## 8. Current state (as of 2026-06-16, Sprint 1)

- ✅ Data pipeline producing `forecast_dataset.csv`.
- ✅ Prophet model trained, tested, persisted; Streamlit dashboard runs (HTTP 200 verified).
- ⏳ Forecasting phase staged for commit; user is reviewing/testing manually before push.
- 🔲 Next up: **Isolation Forest anomaly model** (task #5), then blockchain, then full Streamlit integration + docs + submission.

### 3-sprint plan (21 days, 2026-06-09 → 06-29)
- **Sprint 1** (Jun 9–15): data + AI models
- **Sprint 2** (Jun 16–22): blockchain + Streamlit UI
- **Sprint 3** (Jun 23–29): integration + testing + docs + submission

See `docs/REQUIREMENTS.md` for the full functional/non-functional requirements and acceptance criteria.
