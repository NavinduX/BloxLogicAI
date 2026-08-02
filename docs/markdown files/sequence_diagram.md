# BloxLogicAI Sequence Diagrams

This document contains the sequence diagrams for all major processes within the BloxLogicAI system.

---

## 1. Authentication Processes (Common)

### 1.1 User Signup
```mermaid
sequenceDiagram
    autonumber
    
    actor User as New User
    participant UI as Streamlit UI
    participant Auth as Auth Manager
    participant DB as User Database (CSV)

    User->>UI: Enters Username, Email, Password & Clicks "Signup"
    UI->>Auth: Submit Registration Request
    
    Auth->>Auth: Validate Inputs
    
    alt Invalid Inputs
        Auth-->>UI: Return Validation Error
        UI-->>User: Display Error Message
    else Valid Inputs
        Auth->>DB: Read CSV to check if Username exists
        DB-->>Auth: Return existence status
        
        alt Username Already Exists
            Auth-->>UI: Return "Username already taken"
            UI-->>User: Display Error Message
        else Username is Available
            Auth->>Auth: Cryptographically Hash Password
            Auth->>DB: Append New User Record to CSV (Username, Hash, Email, Role: 'User')
            DB-->>Auth: Confirm Save Success
            Auth-->>UI: Return Registration Success
            UI-->>User: Display Success Message & Redirect to Login
        end
    end
```

### 1.2 User Login
```mermaid
sequenceDiagram
    autonumber
    
    actor User as User / Admin
    participant UI as Streamlit UI
    participant Auth as Auth Manager
    participant DB as User Database (CSV)

    User->>UI: Enters Username, Password & Clicks "Login"
    UI->>Auth: Submit Authentication Request
    
    Auth->>DB: Read CSV to find Username
    DB-->>Auth: Return User Record (Stored Hash, Role)
    
    alt User Not Found
        Auth-->>UI: Return "Invalid Credentials"
        UI-->>User: Display Error Message
    else User Found
        Auth->>Auth: Hash input password and compare
        
        alt Hashes do not match
            Auth-->>UI: Return "Invalid Credentials"
            UI-->>User: Display Error Message
        else Hashes match
            Auth-->>UI: Return Authentication Success (Role)
            UI->>UI: Set User Session State (Logged In = True)
            
            alt Role == 'Admin'
                UI-->>User: Redirect to Admin Dashboard
            else Role == 'User'
                UI-->>User: Redirect to User Dashboard
            end
        end
    end
```

### 1.3 User Signout
```mermaid
sequenceDiagram
    autonumber
    
    actor User as Authenticated User
    participant UI as Streamlit UI

    User->>UI: Clicks "Signout"
    
    UI->>UI: Destroy Session Variables (Logged In = False, Clear Data)
    
    UI-->>User: Redirect to Landing Page / Login Page
```

---

## 2. End-User Processes

### 2.1 View & Download Forecast Data
```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as Streamlit UI
    participant Backend as Python Backend
    participant Prophet as Prophet Model
    participant DB as Historical Data (CSV)

    User->>UI: Selects Forecasting Settings (Months ahead, etc.)
    UI->>Backend: Request Forecast Data
    
    Backend->>DB: Fetch historical data
    DB-->>Backend: Return data
    
    Backend->>Prophet: Pass data & user parameters for Inference
    Prophet-->>Backend: Return predicted values & confidence intervals
    
    Backend-->>UI: Return forecast dataset
    UI-->>User: Render Interactive Charts
    
    User->>UI: Clicks "Download CSV"
    UI->>Backend: Request CSV generation
    Backend-->>UI: Return CSV byte stream
    UI-->>User: Trigger File Download
```

### 2.2 View Anomalies & Suggestions
```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as Streamlit UI
    participant Backend as Python Backend
    participant iForest as Isolation Forest Model

    User->>UI: Navigates to Anomaly Detection
    UI->>Backend: Request Anomaly Scan
    
    Backend->>iForest: Pass recent data points
    iForest-->>Backend: Return identified outliers (-1)
    
    Backend->>Backend: Generate mitigation suggestions for each anomaly
    
    Backend-->>UI: Return Anomalies & Suggestions
    UI-->>User: Render Charts (Red Dots) & Display Suggestion Cards
```

### 2.3 Verify Tea Batches (QR / Batch Number)
```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as Streamlit UI
    participant BC_Mgr as Blockchain Manager
    participant Ledger as ledger.json

    User->>UI: Enters Batch Number OR Scans QR Code
    UI->>BC_Mgr: Submit Batch ID for Verification
    
    BC_Mgr->>Ledger: Read ledger.json
    Ledger-->>BC_Mgr: Return chain data
    
    BC_Mgr->>BC_Mgr: Search for matching Batch ID
    
    alt Batch Not Found
        BC_Mgr-->>UI: Return "Batch not found"
        UI-->>User: Display Error
    else Batch Found
        BC_Mgr->>BC_Mgr: Verify SHA-256 Hash of the specific block
        
        alt Hash is Valid
            BC_Mgr-->>UI: Return Block Data & "Valid" status
            UI-->>User: Display Provenance Data & Green Check
        else Hash is Invalid (Tampered)
            BC_Mgr-->>UI: Return "Tampered" status
            UI-->>User: Display Red Warning Alert
        end
    end
```

### 2.4 Manage Profile (Update Email / Password)
```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as Streamlit UI
    participant Auth as Auth Manager
    participant DB as users.csv

    User->>UI: Navigates to Profile & Enters new Email/Password
    UI->>Auth: Submit Update Request
    
    Auth->>Auth: Validate new inputs
    
    alt Validation Failed
        Auth-->>UI: Return Error
        UI-->>User: Display Validation Error
    else Validation Passed
        Auth->>DB: Read users.csv
        DB-->>Auth: Return current user data
        
        Auth->>Auth: Cryptographically Hash new password (if changed)
        Auth->>DB: Update row in users.csv
        DB-->>Auth: Confirm Save
        
        Auth-->>UI: Return Update Success
        UI-->>User: Display Success Message
    end
```

---

## 3. Administrator Processes

### 3.1 Train & Retrain Models
```mermaid
sequenceDiagram
    autonumber
    
    actor Admin as Administrator
    participant UI as Streamlit UI
    participant Backend as Python Backend
    participant Prophet as FB Prophet (Forecasting)
    participant iForest as Isolation Forest (Anomaly)

    alt Train Forecasting Model
        Admin->>UI: Clicks "Train FB Prophet"
        UI->>Backend: Trigger Forecasting Training
        Backend->>Backend: Fetch & Preprocess Data
        Backend->>Prophet: Feed historical data
        Prophet-->>Backend: Return Trained Prophet Model
        Backend->>Backend: Save prophet_model.pkl
        Backend-->>UI: Return "Forecasting Model Trained"
        UI-->>Admin: Display Success Message
    else Train Anomaly Model
        Admin->>UI: Clicks "Train Isolation Forest"
        UI->>Backend: Trigger Anomaly Training
        Backend->>Backend: Fetch & Preprocess Data
        Backend->>iForest: Feed historical data
        iForest-->>Backend: Return Trained iForest Model
        Backend->>Backend: Save iforest_model.pkl
        Backend-->>UI: Return "Anomaly Model Trained"
        UI-->>Admin: Display Success Message
    end
```

### 3.2 Add New Datasets & Retrain
```mermaid
sequenceDiagram
    autonumber
    
    actor Admin as Administrator
    participant UI as Streamlit UI
    participant Backend as Python Backend
    participant DB as Local Datasets (CSV)

    Admin->>UI: Uploads new CSV dataset
    UI->>Backend: Send CSV File
    
    Backend->>Backend: Validate Columns & Data Types
    
    alt Validation Failed
        Backend-->>UI: Return Error
        UI-->>Admin: Display Data Format Error
    else Validation Passed
        Backend->>DB: Append / Overwrite CSV Data
        DB-->>Backend: Confirm File Save
        
        Backend->>Backend: Trigger Auto-Retrain Pipeline (Prophet/iForest)
        Backend-->>UI: Return "Dataset Updated & Models Retrained"
        UI-->>Admin: Display Success Message
    end
```

### 3.3 Manage Blockchain Ledger
```mermaid
sequenceDiagram
    autonumber
    
    actor Admin as Administrator
    participant UI as Streamlit UI
    participant BC_Mgr as Blockchain Manager
    participant Ledger as ledger.json

    alt Add New Tea Batch
        Admin->>UI: Enters Batch Details & Clicks "Add Batch"
        UI->>BC_Mgr: Submit New Batch Payload
        BC_Mgr->>Ledger: Read previous block hash
        Ledger-->>BC_Mgr: Return previous hash
        BC_Mgr->>BC_Mgr: Calculate SHA-256 (Payload + Prev Hash)
        BC_Mgr->>Ledger: Append New Block to ledger.json
        Ledger-->>BC_Mgr: Confirm Save
        BC_Mgr-->>UI: Return "Batch Added & Secured"
        UI-->>Admin: Display Success Message
    else Audit Ledger
        Admin->>UI: Clicks "Audit/Validate Integrity"
        UI->>BC_Mgr: Trigger Integrity Check
        
        loop For each block
            BC_Mgr->>BC_Mgr: Recalculate SHA-256 Hashes
        end
        
        BC_Mgr-->>UI: Return Audit Results
        UI-->>Admin: Highlight tampered records or confirm integrity
    end
```

### 3.4 Manage Users (Add, Update, Remove)
```mermaid
sequenceDiagram
    autonumber
    
    actor Admin as Administrator
    participant UI as Streamlit UI
    participant Auth as Auth Manager
    participant UsersDB as users.csv

    Admin->>UI: Submits User Action (Add, Update, or Delete)
    UI->>Auth: Request User Management Action
    
    Auth->>UsersDB: Read users.csv
    UsersDB-->>Auth: Return User List
    
    alt Add New User
        Auth->>Auth: Hash Password
        Auth->>UsersDB: Append New Row
    else Update User
        Auth->>UsersDB: Modify Existing Row (Role/Email)
    else Delete User
        Auth->>UsersDB: Remove Row matching Username
    end
    
    UsersDB-->>Auth: Confirm File Update
    Auth-->>UI: Return Success Status
    UI-->>Admin: Refresh User List & Show Success Message
```
