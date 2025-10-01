graph TD
    Start([Theta Updated]) --> MinCheck{Questions answered<br/>≥ 10?}

    MinCheck -->|No| NoChange[NO TIER CHANGE ALLOWED<br/>Minimum questions not met]
    MinCheck -->|Yes| GetCurrent[Get current tier<br/>from current theta]

    NoChange --> End

    GetCurrent --> CurrentTier{Current Tier?}

    CurrentTier -->|C1: -3.0 to -1.0| CheckC1
    CurrentTier -->|C2: -1.0 to 0.0| CheckC2
    CurrentTier -->|C3: 0.0 to 1.0| CheckC3
    CurrentTier -->|C4: 1.0 to 3.0| CheckC4

    CheckC1[Check promotion from C1] --> PromotionWindow
    CheckC2[Check promotion/demotion] --> PromotionWindow
    CheckC3[Check promotion/demotion] --> PromotionWindow
    CheckC4[Check demotion from C4] --> PromotionWindow

    PromotionWindow{Last 10 responses<br/>available?}

    PromotionWindow -->|No| DemotionWindow
    PromotionWindow -->|Yes| CountCorrect[Count correct in<br/>last 10 responses]

    CountCorrect --> PromoteThreshold{Correct count<br/>≥ 7?}

    PromoteThreshold -->|Yes| CanPromote{Can promote<br/>from current tier?}
    PromoteThreshold -->|No| DemotionWindow

    CanPromote -->|C1| PromoteC1[PROMOTE: C1 → C2<br/>New difficulty range: -1.0 to 1.0<br/>New discrimination: 0.7 to 1.7]
    CanPromote -->|C2| PromoteC2[PROMOTE: C2 → C3<br/>New difficulty range: 0.0 to 2.0<br/>New discrimination: 0.8 to 2.0]
    CanPromote -->|C3| PromoteC3[PROMOTE: C3 → C4<br/>New difficulty range: 1.0 to 3.0<br/>New discrimination: 1.0 to 2.5]
    CanPromote -->|C4| NoPromotion[Already at highest tier]

    PromoteC1 --> LogPromotion
    PromoteC2 --> LogPromotion
    PromoteC3 --> LogPromotion
    NoPromotion --> DemotionWindow

    LogPromotion[Log Tier Change:<br/>Performance: 7+/10 correct<br/>Reason: Sustained excellence<br/>New question access granted]

    LogPromotion --> End

    DemotionWindow{Last 10 responses<br/>available?}

    DemotionWindow -->|No| NoChange2[No tier change]
    DemotionWindow -->|Yes| CountCorrect2[Count correct in<br/>last 10 responses]

    NoChange2 --> End

    CountCorrect2 --> DemoteThreshold{Correct count<br/>≤ 3?}

    DemoteThreshold -->|Yes| CanDemote{Can demote<br/>from current tier?}
    DemoteThreshold -->|No| NoChange3[No tier change]

    NoChange3 --> End

    CanDemote -->|C4| DemoteC4[DEMOTE: C4 → C3<br/>New difficulty range: 0.0 to 2.0<br/>Easier questions accessed]
    CanDemote -->|C3| DemoteC3[DEMOTE: C3 → C2<br/>New difficulty range: -1.0 to 1.0]
    CanDemote -->|C2| DemoteC2[DEMOTE: C2 → C1<br/>New difficulty range: -2.0 to 0.0]
    CanDemote -->|C1| NoDemotion[Already at lowest tier]

    DemoteC4 --> LogDemotion
    DemoteC3 --> LogDemotion
    DemoteC2 --> LogDemotion
    NoDemotion --> End

    LogDemotion[Log Tier Change:<br/>Performance: ≤3/10 correct<br/>Reason: Need support<br/>Adjusted question difficulty]

    LogDemotion --> End([Tier Updated<br/>Continue Assessment])

    style PromoteC1 fill:#e8f5e9
    style PromoteC2 fill:#e8f5e9
    style PromoteC3 fill:#e8f5e9
    style DemoteC4 fill:#ffebee
    style DemoteC3 fill:#ffebee
    style DemoteC2 fill:#ffebee
    style MinCheck fill:#fff4e1