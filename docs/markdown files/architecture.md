# BloxLogicAI Architecture & System Diagrams

This document contains industry-standard system diagrams that explain the underlying architecture, data flow, and user interactions of the BloxLogicAI platform.

---

## 1. System Architecture Diagram

This diagram represents the high-level infrastructure of BloxLogicAI. It follows a standard multi-tier architecture, separating the application into the Presentation Layer (Frontend), Application Layer (Backend Logic), AI Engine, and the Data/Security Layer.

```mermaid
flowchart TB
    %% Styling for industry standard look
    classDef actor fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef frontend fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef backend fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef ai fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef data fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    subgraph "External Actors"
        U(["End Users / Stakeholders"]):::actor
        A(["Administrators"]):::actor
    end

    subgraph "Presentation Layer (Streamlit UI)"
        UI_User["User Portal & Dashboard"]:::frontend
        UI_Admin["Admin Management Portal"]:::frontend
    end

    subgraph "Application Layer (Python Core)"
        Auth["Auth & Session Manager"]:::backend
        DP["Data Pipeline & Processor"]:::backend
        BC_Mgr["Blockchain Manager"]:::backend
    end

    subgraph "AI & Analytics Engine"
        Prophet["Facebook Prophet\nForecasting Model"]:::ai
        iForest["Isolation Forest\nAnomaly Detection"]:::ai
    end

    subgraph "Data & Security Layer"
        DB[("Local Datasets\nCSV / Excel")]:::data
        Ledger[("Blockchain Ledger\nJSON / SHA-256")]:::data
    end

    %% Connections
    U -->|"View Insights"| UI_User
    A -->|"Manage System"| UI_Admin

    UI_User <-->|"HTTP / Session"| Auth
    UI_Admin <-->|"HTTP / Session"| Auth

    Auth --> DP
    Auth --> BC_Mgr

    DP <-->|"Read / Write"| DB
    DP -->|"Inference / Training"| Prophet
    DP -->|"Outlier Detection"| iForest
    
    Prophet -.->|"Predictions"| DP
    iForest -.->|"Anomalies"| DP

    BC_Mgr <-->|"Cryptographic Hashing"| Ledger
    DP -->|"Log Data Integrity"| BC_Mgr
```

### Layer Breakdown:
1.  **External Actors:** Represents the human interactions with the system. Users view data; Admins manage it.
2.  **Presentation Layer:** Built entirely with Streamlit, handling the UI rendering and user inputs natively in Python.
3.  **Application Layer:** The core Python logic that handles user sessions, processes data using Pandas/NumPy, and acts as the middleman to the database and blockchain.
4.  **AI Engine:** The isolated machine learning models. They receive cleaned data from the pipeline and return mathematical predictions and anomaly flags.
5.  **Data & Security:** The persistent storage. Datasets are stored locally, while the Custom Blockchain ensures that historical records remain immutable.


