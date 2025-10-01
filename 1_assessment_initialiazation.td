graph TD
    Start([Test Taker Arrives]) --> GetLevel[Client Selects/System Detects<br/>Competence Level]

    GetLevel --> MapTheta{Map to Initial Theta}

    MapTheta -->|Beginner| SetB[Set theta = -1.5<br/>Target: C1 tier]
    MapTheta -->|Intermediate| SetI[Set theta = 0.0<br/>Target: C2 tier]
    MapTheta -->|Advanced| SetA[Set theta = 1.5<br/>Target: C3 tier]
    MapTheta -->|Expert| SetE[Set theta = 2.0<br/>Target: C4 tier]

    SetB --> LoadConfig
    SetI --> LoadConfig
    SetA --> LoadConfig
    SetE --> LoadConfig

    LoadConfig[Load Test Purpose Config] --> ConfigType{Purpose?}

    ConfigType -->|Screening| Screen[5-15 questions<br/>SEM target: 0.5<br/>Fast tier changes]
    ConfigType -->|Diagnostic| Diag[15-40 questions<br/>SEM target: 0.25<br/>Conservative progression]
    ConfigType -->|Placement| Place[10-25 questions<br/>SEM target: 0.35<br/>Balanced approach]

    Screen --> InitVars
    Diag --> InitVars
    Place --> InitVars

    InitVars[Initialize Tracking:<br/>- theta_history = initial<br/>- response_history = empty<br/>- cumulative_responses = empty<br/>- question_count = 0] --> ShowReady

    ShowReady[Display to User:<br/>Assessment customized<br/>Expected question count<br/>Starting difficulty level] --> Ready([Ready for Q1])

    style MapTheta fill:#e1f5ff
    style LoadConfig fill:#fff4e1
    style InitVars fill:#e8f5e9