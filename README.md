# BloxLogicAI

> **An AI and Blockchain-Enabled Supply Chain Forecasting Analysis System for Sri Lanka's Tea Industry**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Data Sources](#data-sources)
- [License](#license)

---

## Overview

**BloxLogicAI** is a lightweight, Python-based web application designed to bring advanced intelligence and transparency to Sri Lanka's tea supply chain. By integrating Machine Learning and Blockchain technology, the platform empowers stakeholders—from tea estate managers to government administrators—to make data-driven decisions, mitigate risks, and guarantee product authenticity.

---

## Key Features

- **AI Forecasting:** Utilizes Facebook Prophet to predict monthly tea export volumes and market demand based on historical data, weather patterns, and macroeconomic indicators.
- **Anomaly Detection:** Employs Scikit-Learn's Isolation Forest to proactively detect supply chain disruptions, fuel price spikes, and production anomalies.
- **Blockchain Traceability:** A custom Python SHA-256 hash chain provides immutable, cryptographically secure records for tea batches, ensuring provenance and transparency.
- **Web Dashboard:** A responsive, interactive user interface built with Streamlit, featuring distinct, role-based portals for both regular Users and system Administrators.

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| **Frontend / UI** | Streamlit |
| **Forecasting Model** | Facebook Prophet |
| **Anomaly Detection** | Scikit-Learn (Isolation Forest) |
| **Data Manipulation** | Pandas, NumPy |
| **Data Visualization**| Plotly, Matplotlib |
| **Blockchain** | Python `hashlib` (SHA-256) |
| **Data Storage** | Local CSV and JSON files |

---

## Project Structure

```text
BloxLogicAI/
├── app/                    # Streamlit UI — entry point, routing, and view components
├── models/                 # AI models — Prophet forecasting and Isolation Forest
├── blockchain/             # Python SHA-256 blockchain simulation and ledger
├── data/                   # Raw source data and processed datasets (CSV/Excel)
├── utils/                  # Data loading pipelines and utility helpers
├── tests/                  # Pytest unit and integration tests
├── docs/                   # Architecture diagrams and user manuals
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## Getting Started

Follow these instructions to set up the project on your local machine for development and testing.

### Prerequisites

- Python 3.9 or higher
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nalantishantha/BloxLogicAI.git
   cd BloxLogicAI
   ```

2. **Create and activate a virtual environment:**
   - **Windows:**
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

To start the Streamlit web server and view the dashboard locally:

```bash
streamlit run app/main.py
```

Once the server is running, open your web browser and navigate to `http://localhost:8501`. 
From the landing page, you can access the **User Portal** or log in to the **Admin Portal** to manage datasets and retrain models.

---

## Testing

The project uses `pytest` for unit testing. To run the test suite and verify the integrity of the application components:

```bash
python -m pytest tests/ -v
```

---

## Data Sources

The machine learning models are trained and validated using real-world data aggregated from the following authoritative sources:

- **Sri Lanka Tea Board:** Annual Report 2023
- **Ministry of Industry (Sri Lanka):** Tea Report 2023
- **Tea Exporters Association:** Market and export reports
- **Sri Lanka Meteorological Department:** Historical climate and weather data
- **Central Bank of Sri Lanka:** Macro-economic indicators (Exchange rates, inflation, etc.)

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
