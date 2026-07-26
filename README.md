# BloxLogicAI

**An AI and Blockchain-Enabled Supply Chain Forecasting Analysis System for Sri Lanka's Tea Industry**

---

## Overview

BloxLogicAI combines three technologies into one lightweight, Python-based web application:

- **AI Forecasting** — Facebook Prophet predicts monthly tea export volumes and market demand
- **Anomaly Detection** — Scikit-Learn Isolation Forest detects supply chain disruptions
- **Blockchain Traceability** — Python SHA-256 hash chain provides immutable tea batch records
- **Web Dashboard** — Streamlit powers both the User Portal and Admin Portal

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/nalantishantha/BloxLogicAI.git
cd BloxLogicAI

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app/main.py
```

Open your browser at `http://localhost:8501`

---

## Project Structure

```
BloxLogicAI/
├── app/                    # Streamlit UI — entry point + portals
├── models/                 # AI models — Prophet + Isolation Forest
├── blockchain/             # Python SHA-256 blockchain simulation
├── data/                   # Raw and processed datasets (CSV/Excel)
├── utils/                  # Data loading + QR code helpers
├── tests/                  # Unit tests
├── docs/                   # Architecture diagrams + user manual
├── requirements.txt
└── README.md
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit |
| Forecasting | Facebook Prophet |
| Anomaly Detection | Scikit-Learn Isolation Forest |
| Blockchain | Python SHA-256 hash chain |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly, Matplotlib |
| Storage | CSV / JSON files |

---

## Data Sources

- Sri Lanka Tea Board Annual Report 2023
- Sri Lanka Ministry of Industry Tea Report 2023
- Tea Exporters Association market reports
- Sri Lanka Meteorological Department climate data
- Central Bank of Sri Lanka macro-economic indicators
