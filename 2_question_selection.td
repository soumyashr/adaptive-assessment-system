graph TD
    Start([Need Next Question]) --> CheckHistory{Response<br/>history exists?}

    CheckHistory -->|No| FirstQ[Use initial theta<br/>No anticipation]
    CheckHistory -->|Yes| CalcAnticipated[Calculate Anticipated Theta]

    FirstQ --> GetTier

    CalcAnticipated --> Analyze[Analyze Last 3 Responses]

    Analyze --> Pattern{Pattern?}

    Pattern -->|All 3 Correct| Up[anticipation = current + max_change × 1.5<br/>Looking ahead for harder content]
    Pattern -->|2/3 Correct| UpMod[anticipation = current + max_change × 0.75<br/>Moderate increase expected]
    Pattern -->|1/3 Correct| DownMod[anticipation = current - max_change × 0.75<br/>Moderate decrease expected]
    Pattern -->|0/3 Correct| Down[anticipation = current - max_change × 1.5<br/>Looking ahead for easier content]

    Up --> ClampTier{Cross >1<br/>tier boundary?}
    UpMod --> ClampTier
    DownMod --> ClampTier
    Down --> ClampTier

    ClampTier -->|Yes| Clamp[Clamp to adjacent<br/>tier boundary<br/>SINGLE-STEP RULE]
    ClampTier -->|No| GetTier

    Clamp --> GetTier[Convert anticipated theta<br/>to tier C1/C2/C3/C4]

    GetTier --> FilterByTier[Filter question bank<br/>by tier difficulty ranges]

    FilterByTier --> HasQuestions{Questions<br/>available?}

    HasQuestions -->|No| Fallback[Use adjusted tier<br/>or all questions]
    HasQuestions -->|Yes| ApplyFloor

    Fallback --> ApplyFloor{Last response<br/>correct?}

    ApplyFloor -->|Yes| MinDiff[Apply minimum difficulty:<br/>difficulty >= last - 0.1<br/>PREVENTS BACKWARD DRIFT]
    ApplyFloor -->|No| ScoreLoop

    MinDiff --> FilterMore{After filter,<br/>questions remain?}

    FilterMore -->|No| RelaxFloor[Relax constraint<br/>Use wider pool]
    FilterMore -->|Yes| ScoreLoop

    RelaxFloor --> ScoreLoop[For Each Candidate Question]

    ScoreLoop --> CalcInfo[Calculate Fisher Information<br/>at ANTICIPATED theta<br/>not current theta]

    CalcInfo --> RTWeight{RT weighting<br/>enabled?}

    RTWeight -->|Yes| ApplyRT[Weighted Info = Info / log RT + 1<br/>Fast correct = higher value]
    RTWeight -->|No| BaseInfo[Use base information]

    ApplyRT --> Penalties
    BaseInfo --> Penalties[Apply Penalties:<br/>- Content overuse: -10% per use<br/>- Item exposure: -20% per exposure]

    Penalties --> ProgBonus{Last response<br/>correct AND<br/>difficulty tracking?}

    ProgBonus -->|Difficulty > last + 0.05| Bonus20[+20% progression bonus<br/>REWARDS UPWARD MOVEMENT]
    ProgBonus -->|Difficulty ≈ last ± 0.05| Bonus10[+10% progression bonus]
    ProgBonus -->|No| NoBonus[No bonus]

    Bonus20 --> AdjustedScore
    Bonus10 --> AdjustedScore
    NoBonus --> AdjustedScore[Calculate:<br/>adjusted_score = info × penalties × bonus]

    AdjustedScore --> MoreQuestions{More candidates<br/>to score?}

    MoreQuestions -->|Yes| ScoreLoop
    MoreQuestions -->|No| SelectBest[Select question with<br/>HIGHEST adjusted_score]

    SelectBest --> UpdateTracking[Update Tracking:<br/>- Content area usage count<br/>- Item exposure count<br/>- last_question_difficulty]

    UpdateTracking --> LogSelection[Log Selection:<br/>difficulty, discrimination,<br/>information, score, bonuses]

    LogSelection --> Present([Present Question<br/>to Test Taker])

    style CalcAnticipated fill:#e1f5ff
    style ClampTier fill:#ffebee
    style MinDiff fill:#fff4e1
    style CalcInfo fill:#e8f5e9
    style SelectBest fill:#f3e5f5