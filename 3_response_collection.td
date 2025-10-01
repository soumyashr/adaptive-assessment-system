graph TD
    Start([Question Presented]) --> RTEnabled{Response Time<br/>tracking enabled?}

    RTEnabled -->|Yes| StartTimer[Start Timer]
    RTEnabled -->|No| WaitResponse

    StartTimer --> WaitResponse[Wait for Test Taker Response]

    WaitResponse --> Response{Response<br/>Received}

    Response -->|Correct| RecordCorrect[Record: is_correct = True]
    Response -->|Incorrect| RecordIncorrect[Record: is_correct = False]

    RecordCorrect --> StopTimer
    RecordIncorrect --> StopTimer{Timer running?}

    StopTimer -->|Yes| CaptureRT[Capture Response Time]
    StopTimer -->|No| BuildTuple

    CaptureRT --> AnalyzeRT[Analyze RT Pattern]

    AnalyzeRT --> RTPattern{RT vs Expected}

    RTPattern -->|Fast Correct<br/>RT < 0.7 × expected| HighConf[Flag: High Confidence<br/>response_time_adjustment = +0.05]
    RTPattern -->|Slow Correct<br/>RT > 2.0 × expected| LowConf[Flag: Low Confidence<br/>response_time_adjustment = -0.02]
    RTPattern -->|Slow Incorrect<br/>RT > 1.5 × expected| Struggle[Flag: Struggled<br/>response_time_adjustment = -0.05]
    RTPattern -->|Normal| NoFlag[No RT adjustment]

    HighConf --> StoreRT
    LowConf --> StoreRT
    Struggle --> StoreRT
    NoFlag --> StoreRT[Store RT in:<br/>question_response_times list]

    StoreRT --> BuildTuple

    BuildTuple[Build Response Tuple:<br/>is_correct, difficulty_b,<br/>discrimination_a, guessing_c]

    BuildTuple --> AddToLists[Add to Lists:<br/>1. responses<br/>2. response_history<br/>3. cumulative_responses]

    AddToLists --> IncrementCount[Increment:<br/>questions_answered++]

    IncrementCount --> UpdateUI[Update UI:<br/>Progress bar<br/>Questions remaining<br/>Current performance]

    UpdateUI --> Ready([Ready for<br/>Theta Update])

    style RTEnabled fill:#e1f5ff
    style AnalyzeRT fill:#fff4e1
    style BuildTuple fill:#e8f5e9