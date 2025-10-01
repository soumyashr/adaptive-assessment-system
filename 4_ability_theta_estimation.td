graph TD
    Start([Response Recorded]) --> UseAll[Use ALL cumulative responses<br/>NOT just latest<br/>KEY: Stability through history]

    UseAll --> EarlyCheck{Question number<br/>≤ 5?}

    EarlyCheck -->|Yes| EarlyLimit[EARLY PROTECTION:<br/>max_change = ±0.2<br/>smoothing_alpha = 0.3<br/>Very conservative]
    EarlyCheck -->|No| QuestionCheck{Question number<br/>≤ 10?}

    QuestionCheck -->|Yes| MidLimit[MODERATE PROTECTION:<br/>max_change = ±0.3<br/>smoothing_alpha = 0.4]
    QuestionCheck -->|No| FullLimit[STANDARD UPDATE:<br/>max_change = ±0.3<br/>smoothing_alpha = 0.5-0.7<br/>Gradually less conservative]

    EarlyLimit --> NRStart
    MidLimit --> NRStart
    FullLimit --> NRStart[Newton-Raphson Iteration<br/>Max 10 iterations]

    NRStart --> NRLoop[Calculate for all responses:<br/>likelihood_derivative<br/>second_derivative]

    NRLoop --> Converge{Converged?<br/>change < 0.001}

    Converge -->|Yes| Smoothing
    Converge -->|No| CalcDelta[Calculate:<br/>delta = -derivative / second_derivative]

    CalcDelta --> ConsecCheck{Consecutive<br/>responses detected?}

    ConsecCheck -->|Yes 3+ same| UseJump[Use adaptive jump size<br/>based on streak length]
    ConsecCheck -->|No| UseMax[Use max_change limit]

    UseJump --> ClampDelta
    UseMax --> ClampDelta[Clamp delta:<br/>|delta| ≤ max_change]

    ClampDelta --> TotalCheck{Total iteration<br/>change > 1.0?}

    TotalCheck -->|Yes| Budget[Enforce remaining budget<br/>Prevent runaway changes]
    TotalCheck -->|No| ApplyDelta[Apply delta to theta]

    Budget --> ApplyDelta

    ApplyDelta --> BoundCheck{Within bounds<br/>-3.0 to +3.0?}

    BoundCheck -->|No| EnforceBounds[Clamp to bounds]
    BoundCheck -->|Yes| NextIter{More iterations<br/>needed?}

    EnforceBounds --> NextIter

    NextIter -->|Yes| NRLoop
    NextIter -->|No| Smoothing[Apply Exponential Smoothing:<br/>new = alpha × calculated + 1-alpha × current<br/>PREVENTS WILD SWINGS]

    Smoothing --> FinalEarlyCheck{Question ≤ 5<br/>AND<br/>|change| > 0.2?}

    FinalEarlyCheck -->|Yes| FinalClamp[FINAL EARLY CLAMP:<br/>Force to ±0.2 max]
    FinalEarlyCheck -->|No| AbsoluteCheck{|change| > 1.0?}

    FinalClamp --> AbsoluteCheck

    AbsoluteCheck -->|Yes| FallbackEAP[SAFETY FALLBACK:<br/>Use EAP estimate<br/>Bayesian posterior]
    AbsoluteCheck -->|No| RTAdjust

    FallbackEAP --> RTAdjust{RT adjustment<br/>enabled?}

    RTAdjust -->|Yes| ApplyRTAdj[Apply RT-based adjustment<br/>Fast correct: +0.05<br/>Slow incorrect: -0.05]
    RTAdjust -->|No| UpdateHistory

    ApplyRTAdj --> UpdateHistory[Update theta_history<br/>Update current_theta<br/>Log change details]

    UpdateHistory --> LogUpdate[Log Update:<br/>old theta → new theta<br/>change amount<br/>method used<br/>convergence status]

    LogUpdate --> Ready([Updated Theta<br/>Ready for Next Step])

    style EarlyLimit fill:#ffebee
    style Smoothing fill:#e1f5ff
    style FinalClamp fill:#ffebee
    style FallbackEAP fill:#fff4e1