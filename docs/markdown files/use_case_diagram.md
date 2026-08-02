# BloxLogicAI Use Case Diagram

This Use Case Diagram outlines the specific interactions and capabilities available to the two primary actors within the BloxLogicAI system: **End Users** and **Administrators**.

```mermaid
flowchart LR
    %% Define styles for clarity
    classDef actorStyle fill:#e1f5fe,stroke:#0288d1,stroke-width:3px,font-weight:bold;
    classDef commonUseCase fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef userUseCase fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef adminUseCase fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    %% Actor on the Left
    User["👤 End User"]:::actorStyle

    %% System Boundary in the Middle
    subgraph BloxLogicAI ["BloxLogicAI System Boundary"]
        direction TB
        
        %% Common Use Cases
        UC_Login(["Login"]):::commonUseCase
        UC_Signup(["Signup"]):::commonUseCase
        UC_Signout(["Signout"]):::commonUseCase
        
        %% User Specific Use Cases
        UC_ViewForecast(["See Forecast Data"]):::userUseCase
        UC_DownloadCSV(["Download Forecast Data (CSV)"]):::userUseCase
        UC_ViewAnomaly(["See Anomaly Detection"]):::userUseCase
        UC_VerifyBC(["Verify Blockchain Ledger\n(Scan QR or Enter Batch Number)"]):::userUseCase
        UC_Profile(["Manage User Profile"]):::userUseCase
        
        %% Admin Specific Use Cases
        UC_DataMgmt(["Dataset Management\n(Add new datasets for models)"]):::adminUseCase
        UC_Train(["Train & Retrain Models"]):::adminUseCase
        UC_ManageBC(["Manage Blockchain Ledger"]):::adminUseCase
        UC_Analyze(["Analyze"]):::adminUseCase
        UC_UserMgmt(["User Management"]):::adminUseCase
    end

    %% Actor on the Right
    Admin["🛠️ Administrator"]:::actorStyle

    %% Connect End User (Left) to Cases
    User --> UC_Login
    User --> UC_Signup
    User --> UC_Signout
    
    User --> UC_ViewForecast
    User --> UC_DownloadCSV
    User --> UC_ViewAnomaly
    User --> UC_VerifyBC
    User --> UC_Profile

    %% Connect Admin (Right) to Cases using undirected associations
    UC_Login --- Admin
    UC_Signup --- Admin
    UC_Signout --- Admin
    
    UC_DataMgmt --- Admin
    UC_Train --- Admin
    UC_ManageBC --- Admin
    UC_Analyze --- Admin
    UC_UserMgmt --- Admin
```
