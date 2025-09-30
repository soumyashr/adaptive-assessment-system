import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';


const AdaptiveAssessment = () => {
  // State management
  const [currentUser, setCurrentUser] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState('');
  const [loading, setLoading] = useState(false);
  const [assessmentComplete, setAssessmentComplete] = useState(false);
  const [results, setResults] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [loginData, setLoginData] = useState({ username: '', competenceLevel: 'C1' });
  const [showLogin, setShowLogin] = useState(true);
  const [error, setError] = useState(null);

  // NEW: Real-time tracking states
  const [liveResponses, setLiveResponses] = useState([]);
  const [questionDifficulties, setQuestionDifficulties] = useState([]);

  const API_BASE = 'http://localhost:8000/api';
  const [currentQuestionDifficulty, setCurrentQuestionDifficulty] = useState(null);


  // Tier color mapping
  const tierColors = {
    'C1': '#ef4444',
    'C2': '#f97316',
    'C3': '#eab308',
    'C4': '#22c55e'
  };

  // Competence levels
  const competenceLevels = [
    { value: 'C1', label: 'C1 - Beginner', description: 'Basic vocabulary understanding' },
    { value: 'C2', label: 'C2 - Intermediate', description: 'Good vocabulary knowledge' },
    { value: 'C3', label: 'C3 - Advanced', description: 'Strong vocabulary skills' },
    { value: 'C4', label: 'C4 - Expert', description: 'Exceptional vocabulary mastery' }
  ];

  const getDisplayTheta = () => {

    // Active session theta takes priority
    if (currentSession?.theta !== undefined) {
      return currentSession.theta;
    }
    // Fall back to user's last proficiency for vocabulary
    if (userStats?.proficiencies?.length > 0) {
      const vocabProficiency = userStats.proficiencies.find(p => p.subject === 'Vocabulary');
      return vocabProficiency?.theta || -1.5;
    }
    return -1.5;
  };

  // Generate ICC curve data
  const generateICCData = useCallback((theta) => {
    const data = [];
    for (let x = -3; x <= 3; x += 0.1) {
      const p = 0.25 + (0.75) / (1 + Math.exp(-1.2 * (x - (theta || 0))));
      data.push({ x: parseFloat(x.toFixed(1)), p: parseFloat(p.toFixed(3)) });
    }
    return data;
  }, []);

  // Custom dot component for theta progression
  const ThetaDot = (props) => {
    const { cx, cy, payload } = props;
    if (!payload) return null;

    const color = payload.correct ? '#22C55E' : '#EF4444'; // Green for correct, red for incorrect

    return (
      <circle
        cx={cx}
        cy={cy}
        r={4}
        fill={color}
        stroke={color}
        strokeWidth={1}
      />
    );
  };

  // FIXED: Generate real-time theta progression with proper data handling
  const generateThetaProgression = useCallback((liveData, finalData) => {
    // Use live data during assessment, final data after completion
    const dataSource = assessmentComplete ? finalData : liveData;
    if (!dataSource || dataSource.length === 0) return [];

    console.log('🎯 Generating Theta Progression:', {
      assessmentComplete,
      liveDataLength: liveData?.length || 0,
      finalDataLength: finalData?.length || 0,
      usingSource: assessmentComplete ? 'final' : 'live'
    });

    return dataSource.map((resp, idx) => {
      const thetaValue = resp.theta_after || resp.theta || 0;
      const isCorrect = resp.is_correct !== undefined ? resp.is_correct : resp.correct;

      console.log(`Question ${idx + 1}: correct=${isCorrect} (${typeof isCorrect}), theta=${thetaValue}`);

      return {
        question: idx + 1,
        theta: parseFloat(thetaValue.toFixed(2)),
        correct: Boolean(isCorrect), // Ensure boolean
        difficulty: parseFloat((resp.difficulty || 0).toFixed(2))
      };
    });
  }, [assessmentComplete]);

  // const generateDifficultyData = useCallback((liveData, finalData) => {
  //   // Use final data if assessment is complete, otherwise live data
  //
  //   const dataSource = assessmentComplete ? finalData : liveData;
  //
  //   if (!dataSource || dataSource.length === 0) return [];
  //
  //   console.log("=== SCATTER CHART DATA ===", {
  //     assessmentComplete,
  //     usingSource: assessmentComplete ? 'backend' : 'live',
  //     dataLength: dataSource.length
  //   });
  //
  //   return dataSource.map((resp, idx) => {
  //     const isCorrect = Boolean(resp.is_correct !== undefined ? resp.is_correct : resp.correct);
  //     const difficulty = resp.difficulty || 0;
  //     const thetaAfter = resp.theta_after || resp.theta || 0;
  //
  //     return {
  //       x: parseFloat(difficulty.toFixed(2)),
  //       y: parseFloat(thetaAfter.toFixed(2)),
  //       correct: isCorrect,
  //       question: idx + 1,
  //       questionId: resp.question_id || `q_${idx}`,
  //       timestamp: resp.timestamp || idx
  //     };
  //   });
  // }, [assessmentComplete]);

  const generateDifficultyData = useCallback((responses, currentDifficulty, currentTheta) => {
    const scatterData = [];

    // Add all answered questions
    if (responses && responses.length > 0) {
      responses.forEach((resp, idx) => {
        const isCorrect = Boolean(resp.is_correct !== undefined ? resp.is_correct : resp.correct);
        scatterData.push({
          x: parseFloat((resp.difficulty ?? 0).toFixed(2)),
          y: parseFloat((resp.theta_after ?? 0).toFixed(2)),
          correct: isCorrect,
          question: idx + 1,
          type: 'answered'
        });
      });
    }

    // Add current unanswered question as preview (black/gray dot)
    if (currentDifficulty !== null && currentTheta !== undefined) {
      scatterData.push({
        x: parseFloat((currentDifficulty).toFixed(2)),
        y: parseFloat(currentTheta.toFixed(2)),
        correct: null, // null = preview/unanswered
        question: responses.length + 1,
        type: 'current'
      });
    }
    console.log('Now scatterData: ', scatterData)
    return scatterData;
  }, []);
  // API error handler
  const handleApiError = (error, context) => {
    console.error(`Error in ${context}:`, error);
    setError(`Failed to ${context}. Please check if the backend server is running.`);
    setLoading(false);
  };

  // Login function
  const login = async () => {
    if (!loginData.username.trim()) {
      setError('Please enter a username');
      return;
    }
    console.log('About to make API call...'); // ← Add this line
    setLoading(true);
    setError(null);

    setLoading(true);
    setError(null);

    // console.log('Current loginData:', loginData);
    // console.log('Username:', loginData.username);
    // console.log('Loading state:', loading);


    try {
      // console.log('before calling api')
      const response = await fetch(`${API_BASE}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginData.username.trim(),
          competence_level: loginData.competenceLevel
        })
      });
      // console.log('response:', response)

      if (response.ok) {
        const user = await response.json();
        // console.log('user from API call /users >>:', user)
        setCurrentUser(user);
        setShowLogin(false);
        await loadUserStats(loginData.username.trim());
      } else {
        throw new Error('Login failed');
      }
    } catch (error) {
      handleApiError(error, 'login');
    }
  };

  // Load user statistics
  const loadUserStats = async (username) => {
    try {
      const response = await fetch(`${API_BASE}/users/${username}/proficiency`);
      if (response.ok) {
        const stats = await response.json();
        console.log('stats from API call /users/${username}/proficiency>>:', stats)
        setUserStats(stats);
        console.log('setUserStats() done')
      }
    } catch (error) {
      console.log('No previous stats found for user');
    }
  };

  // Start assessment
  const startAssessment = async (subject = 'Vocabulary') => {
    console.log('🚀 startAssessment function called with subject:', subject);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/assessments/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: currentUser.username,
          subject: subject
        })
      });
      console.log('after calling assessments/start , response> : ', response)
      if (response.ok) {
        const session = await response.json();
        console.log('Initial question from API:', {
          question_object: session.current_question,
          has_difficulty_b: 'difficulty_b' in session.current_question,
          difficulty_b_value: session.current_question?.difficulty_b,
          all_keys: Object.keys(session.current_question || {})
        });
        setCurrentSession(session);
        setCurrentQuestion(session.current_question);
        setAssessmentComplete(false);
        setResults(null);

        // NEW: Reset live tracking
        setLiveResponses([]);
        setQuestionDifficulties([]);

        // Newly added Set initial current question difficulty
        setCurrentQuestionDifficulty(
          session.current_question?.difficulty_b || 0
        );
      } else {
        throw new Error('Failed to start assessment');
      }
    } catch (error) {
      handleApiError(error, 'start assessment');
    }
    setLoading(false);
  };

  // Submit answer with REAL answer validation
  const submitAnswer = async () => {
    if (!selectedOption || !currentSession || !currentQuestion) return;

    console.log('🎯 Submitting Answer:');
    console.log('Selected option:', selectedOption);
    console.log('Question ID:', currentQuestion.id);
    console.log('Current question:', currentQuestion);
    console.log('Correct answer should be:', currentQuestion.correct_option);

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/assessments/${currentSession.session_id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          selected_option: selectedOption
        })
      });

      if (response.ok) {
        const updatedSession = await response.json();

        // DEBUG: Log full backend response
        console.log('FULL BACKEND RESPONSE:', JSON.stringify(updatedSession, null, 2));

        // ✅ CHECK COMPLETION FIRST
        if (updatedSession.completed) {
          console.log('Assessment completed, processing...');
          setCurrentSession(updatedSession);
          setAssessmentComplete(true);

          try {
            console.log('Loading results...');
            await loadResults(updatedSession.session_id);
            console.log('Results loaded successfully');
          } catch (error) {
            console.error('Error loading results:', error);
          }

          try {
            console.log('Loading user stats...');
            await loadUserStats(currentUser.username);
            console.log('User stats loaded successfully');
          } catch (error) {
            console.error('Error loading user stats:', error);
          }

          setSelectedOption('');
          return; // ✅ EXIT HERE
        }

        // ✅ ONLY PROCESS ANSWER DATA IF NOT COMPLETED
        console.log('Next question from API:', {
          question_object: updatedSession.current_question,
          has_difficulty_b: 'difficulty_b' in updatedSession.current_question,
          difficulty_b_value: updatedSession.current_question?.difficulty_b,
          all_keys: Object.keys(updatedSession.current_question || {})
        });

        // ✅ SIMPLIFIED: Use backend validation, fallback to string comparison
        let wasCorrect;
        if (updatedSession.last_response_correct !== undefined && updatedSession.last_response_correct !== null) {
          wasCorrect = Boolean(updatedSession.last_response_correct);
          console.log('✅ Using backend validation:', wasCorrect);
        } else {
          // Simple string comparison as fallback (handle type coercion)
          wasCorrect = String(selectedOption) === String(currentQuestion.correct_option);
          console.log('⚠️ Using client-side fallback:', wasCorrect);
        }

        console.log('🚨 VALIDATION DEBUG:', {
          selectedOption: selectedOption,
          selectedType: typeof selectedOption,
          correctOption: currentQuestion.correct_option,
          correctType: typeof currentQuestion.correct_option,
          areEqual: selectedOption === currentQuestion.correct_option,
          backendProvided: updatedSession.last_response_correct,
          backendType: typeof updatedSession.last_response_correct,
          finalWasCorrect: wasCorrect
        });

        const questionDifficulty = currentQuestion.difficulty_b ||
                                 currentQuestion.difficulty ||
                                 currentQuestion.item_difficulty ||
                                 currentQuestion.b_parameter ||
                                 parseFloat(currentQuestion.tier_difficulty) ||
                                 0.0;

        console.log('🎯 Question Difficulty Debug:', {
          question_id: currentQuestion.id,
          difficulty_b: currentQuestion.difficulty_b,
          difficulty: currentQuestion.difficulty,
          final_difficulty: questionDifficulty,
          question_object_keys: Object.keys(currentQuestion)
        });

        const responseData = {
          question: currentQuestion.question,
          selected: selectedOption,
          correct_option: currentQuestion.correct_option,
          theta_before: currentSession.theta,
          theta_after: updatedSession.theta,
          theta: updatedSession.theta,
          is_correct: Boolean(wasCorrect),
          correct: Boolean(wasCorrect),
          difficulty: questionDifficulty,
          question_id: currentQuestion.id,
          question_number: liveResponses.length + 1,
          timestamp: Date.now()
        };

        console.log('📊 Adding response data:', {
          ...responseData,
          correctType: typeof responseData.correct,
          correctValue: responseData.correct
        });

        setLiveResponses(prev => {
          const newResponses = [...prev, responseData];
          console.log('STATE UPDATE DEBUG:', newResponses.map((r, i) => ({
            question: i + 1,
            selected: r.selected,
            correctOption: r.correct_option,
            correct: r.correct,
            wasActuallyCorrect: r.selected === r.correct_option
          })));
          return newResponses;
        });

        setQuestionDifficulties(prev => [...prev, questionDifficulty]);

        // ✅ UPDATE SESSION AND NEXT QUESTION
        setCurrentSession(updatedSession);
        setCurrentQuestion(updatedSession.current_question);
        // Newly added
        setCurrentQuestionDifficulty(
            updatedSession.current_question?.difficulty_b || null
        );
        setSelectedOption('');

      } else {
        throw new Error('Failed to submit answer');
      }
    } catch (error) {
      handleApiError(error, 'submit answer');
    }
    setLoading(false);
  };



  // Load assessment results
  const loadResults = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/assessments/${sessionId}/results`);
      if (response.ok) {
        const resultsData = await response.json();
        console.log('📈 Final results loaded:', resultsData);
        setResults(resultsData);
      }
    } catch (error) {
      console.error('Failed to load results:', error);
    }
  };

  // Get current theta color
  const getCurrentThetaColor = (theta) => {
    if (theta < -1.0) return tierColors['C1'];
    if (theta < 0.0) return tierColors['C2'];
    if (theta < 1.0) return tierColors['C3'];
    return tierColors['C4'];
  };

  // Get theta tier label
  const getThetaTierLabel = (theta) => {
    if (theta < -1.0) return 'Beginner';
    if (theta < 0.0) return 'Intermediate';
    if (theta < 1.0) return 'Advanced';
    return 'Expert';
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (currentQuestion && !loading) {
        const key = event.key.toLowerCase();
        if (['a', 'b', 'c', 'd'].includes(key)) {
          setSelectedOption(key.toUpperCase());
        } else if (event.key === 'Enter' && selectedOption) {
          submitAnswer();
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentQuestion, loading, selectedOption]);

  // Login Screen
  if (showLogin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-gray-800 backdrop-blur-sm rounded-xl p-8 w-full max-w-md shadow-2xl border border-gray-700">
          <div className="text-center mb-8">
            <div className="text-4xl mb-4">🧠</div>
            <h1 className="text-3xl font-bold text-white mb-2">
              Adaptive Assessment
            </h1>
            <p className="text-gray-400">IRT-powered intelligent testing</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-gray-300 mb-2 font-medium">Username</label>
              <input
                type="text"
                value={loginData.username}
                onChange={(e) => setLoginData({...loginData, username: e.target.value})}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-600 transition-all"
                placeholder="Enter your username"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-2 font-medium">Initial Competence Level</label>
              <select
                value={loginData.competenceLevel}
                onChange={(e) => setLoginData({...loginData, competenceLevel: e.target.value})}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-600 transition-all"
                disabled={loading}
              >
                {competenceLevels.map(level => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
              <p className="text-gray-500 text-xs mt-1">
                {competenceLevels.find(l => l.value === loginData.competenceLevel)?.description}
              </p>
            </div>

            <button
              onClick={login}
              disabled={!loginData.username.trim() || loading}

              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg px-4 py-3 font-medium transition-all transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"

            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Logging in...
                </div>
              ) : 'Begin Assessment'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // UPDATED: Generate chart data with FIXED real-time values
  const displayTheta = getDisplayTheta();
  // commented below for testing, if testing passes, remove commented code else un-comment below and remove new code
  // const iccData = generateICCData(currentSession?.theta);//
 const iccData = generateICCData(displayTheta);


  const thetaProgression = generateThetaProgression(liveResponses, results?.responses);
  // const difficultyData = generateDifficultyData(liveResponses, results?.responses);
  // Newly added
  const difficultyData = generateDifficultyData(
    liveResponses,
    currentQuestionDifficulty,
    currentSession?.theta
  );

  // Main Application
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">📊</div>
              <h1 className="text-xl font-bold text-yellow-400">Adaptive Assessment</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-gray-300">
                Welcome, <span className="text-white font-medium">{currentUser?.username}</span>
              </div>
              <button
                onClick={() => {
                  setShowLogin(true);
                  setCurrentUser(null);
                  setCurrentSession(null);
                  setCurrentQuestion(null);
                  setAssessmentComplete(false);
                  setResults(null);
                  setLiveResponses([]);
                  setQuestionDifficulties([]);
                  setCurrentQuestionDifficulty(null);
                }}
                className="text-gray-400 hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-600 text-white px-6 py-3">
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-white hover:text-gray-200"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - ICC Chart - UPDATED */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-2 text-gray-200">Item Characteristic Curve</h3>
            <p className="text-xs text-gray-400 mb-3">
              Shows probability of correct response across ability levels. Vertical line indicates your current θ.
            </p>
            <div className="h-64 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={iccData}>
                  <XAxis
                    dataKey="x"
                    domain={[-3, 3]}
                    type="number"
                    tickFormatter={(value) => value.toFixed(0)}
                    stroke="#9CA3AF"
                    fontSize={12}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tickFormatter={(value) => value.toFixed(1)}
                    stroke="#9CA3AF"
                    fontSize={12}
                  />
                  <Tooltip
                    formatter={(value, name) => [value.toFixed(3), 'Probability']}
                    labelFormatter={(label) => `θ: ${label}`}
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '6px',
                      color: '#fff'
                    }}
                  />
                  {/* Current theta reference line */}
                  {currentSession?.theta !== undefined && currentSession?.theta !== null && (
                    <ReferenceLine
                      x={currentSession.theta}
                      stroke={getCurrentThetaColor(currentSession.theta)}
                      strokeWidth={2}
                      strokeDasharray="3 3"
                    />
                  )}

                  <Line
                    type="monotone"
                    dataKey="p"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Current Proficiency */}
            {/*commented below for testing, if testing passes, remove commented code else un-comment below and remove new code*/}
            {/*<div>*/}
            {/*  <h4 className="text-sm font-medium mb-3 text-gray-300">Current Proficiency</h4>*/}
            {/*  <div className="bg-gray-700 rounded-lg p-3">*/}
            {/*    <div className="flex justify-between items-center">*/}
            {/*      <span className="text-gray-300">Vocabulary</span>*/}
            {/*      <span*/}
            {/*        className="px-3 py-1 rounded-full text-xs font-medium text-white"*/}
            {/*        style={{ backgroundColor: getCurrentThetaColor(currentSession?.theta || -1.5) }}*/}
            {/*      >*/}
            {/*        {getThetaTierLabel(currentSession?.theta || -1.5)}*/}
            {/*      </span>*/}
            {/*    </div>*/}
            {/*    {currentSession && (*/}
            {/*      <div className="mt-2 text-sm text-gray-400">*/}
            {/*        θ = {currentSession.theta?.toFixed(3)}, SEM = {currentSession.sem?.toFixed(3)}*/}
            {/*      </div>*/}
            {/*    )}*/}
            {/*  </div>*/}
            {/*</div>*/}
            {/* Current Proficiency - Show even without active session */}
            <div>
              <h4 className="text-sm font-medium mb-3 text-gray-300">Current Proficiency</h4>
              <div className="bg-gray-700 rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Vocabulary</span>
                  <span
                    className="px-3 py-1 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: getCurrentThetaColor(displayTheta) }}
                  >
                    {getThetaTierLabel(displayTheta)}
                  </span>
                </div>
                <div className="mt-2 text-sm text-gray-400">
                  θ = {displayTheta.toFixed(3)}
                  {currentSession && `, SEM = ${currentSession.sem?.toFixed(3)}`}
                </div>
              </div>
            </div>
          </div>

          {/* Center Column - Assessment Interface */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            {!currentSession ? (
              <div className="text-center">
                <div className="mb-6">
                  <div className="text-6xl mb-4">🎯</div>
                  <h2 className="text-2xl font-semibold mb-4 text-gray-200">Ready to Begin?</h2>
                  <p className="text-gray-400 mb-6">
                    Take an adaptive vocabulary assessment that adjusts to your ability level in real-time.
                  </p>
                </div>

                {userStats && userStats.proficiencies.length > 0 && (
                  <div className="mb-6 p-4 bg-gray-700/50 rounded-lg">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">Previous Results</h3>
                    {userStats.proficiencies.map(prof => (
                      <div key={prof.subject} className="text-sm text-gray-400">
                        {prof.subject}: {prof.tier} (θ={prof.theta.toFixed(2)})
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => startAssessment('Vocabulary')}
                  // disabled={loading}
                  className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg px-8 py-3 font-medium transition-all transform hover:scale-105 disabled:scale-100"
                >

                  {/*{loading ? 'Starting...' : 'Start Vocabulary Assessment'}*/}
                  Start Assessment
                </button>
              </div>
            ) : assessmentComplete ? (
              <div className="text-center">
                <div className="text-6xl mb-4">🎉</div>
                <h2 className="text-2xl font-semibold mb-6 text-green-400">Assessment Complete!</h2>

                {results && (
                  <div className="space-y-4 mb-8">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="text-sm text-gray-300">Final Level</div>
                        <div className="text-xl font-semibold text-white">{results.tier}</div>
                      </div>
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="text-sm text-gray-300">Accuracy</div>
                        <div className="text-xl font-semibold text-white">{(results.accuracy * 100).toFixed(1)}%</div>
                      </div>
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="text-sm text-gray-300">Questions</div>
                        <div className="text-xl font-semibold text-white">{results.questions_asked}</div>
                      </div>
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="text-sm text-gray-300">Final θ</div>
                        <div className="text-xl font-semibold text-white">{results.final_theta?.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={() => startAssessment('Vocabulary')}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg px-6 py-3 font-medium transition-all"
                >
                  Take Another Assessment
                </button>
              </div>
            ) : currentQuestion ? (
              <div>
                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-sm text-gray-400 mb-2">
                    <span>Question {currentSession.questions_asked + 1}</span>
                    <span>θ: {currentSession.theta?.toFixed(2) ?? 'N/A'} | SEM: {currentSession.sem?.toFixed(2) ?? 'NA'}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min((currentSession.questions_asked / 20) * 100, 100)}%`,
                        backgroundColor: getCurrentThetaColor(currentSession?.theta || -1.5)
                      }}
                    ></div>
                  </div>
                </div>

                {/* Question */}
                <div className="mb-8">
                  <h2 className="text-xl font-medium mb-6 text-gray-200 leading-relaxed">
                    {currentQuestion.question}
                  </h2>

                  <div className="space-y-3">
                    {[
                      { key: 'A', text: currentQuestion.option_a },
                      { key: 'B', text: currentQuestion.option_b },
                      { key: 'C', text: currentQuestion.option_c },
                      { key: 'D', text: currentQuestion.option_d }
                    ].map((option) => (
                      <label
                        key={option.key}
                        className={`flex items-center p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-gray-700/30 ${
                          selectedOption === option.key 
                            ? 'border-blue-500 bg-blue-500/10 ring-1 ring-blue-500/20' 
                            : 'border-gray-600 hover:border-gray-500'
                        }`}
                      >
                        <input
                          type="radio"
                          name="option"
                          value={option.key}
                          checked={selectedOption === option.key}
                          onChange={(e) => setSelectedOption(e.target.value)}
                          disabled={loading}
                          className="mr-3"
                        />
                        <span className="font-medium mr-3 text-gray-300">{option.key}.</span>
                        <span className="text-gray-200">{option.text}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-between">
                  <button
                    onClick={() => setSelectedOption('')}
                    disabled={loading || !selectedOption}
                    className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 font-medium transition-colors"
                  >
                    Clear
                  </button>
                  <button
                    onClick={submitAnswer}
                    disabled={!selectedOption || loading}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg px-8 py-2 font-medium transition-all"
                  >
                    {loading ? (
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting...
                      </div>
                    ) : 'Submit Answer'}
                  </button>
                </div>

                {/* Keyboard Shortcuts Hint */}
                <div className="mt-4 text-xs text-gray-500 text-center">
                  Press A, B, C, or D keys to select • Enter to submit
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                Loading...
              </div>
            )}
          </div>

          {/* Right Column - Statistics & Charts */}
          <div className="space-y-4">
            {/* Proficiency Legend */}
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h3 className="text-sm font-medium mb-4 text-gray-200">Proficiency Levels</h3>
              <div className="space-y-3">
                {[
                  { label: 'Beginner', color: tierColors.C1, range: 'θ < -1.0' },
                  { label: 'Intermediate', color: tierColors.C2, range: '-1.0 ≤ θ < 0.0' },
                  { label: 'Advanced', color: tierColors.C3, range: '0.0 ≤ θ < 1.0' },
                  { label: 'Expert', color: tierColors.C4, range: 'θ ≥ 1.0' }
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div
                        className="w-3 h-3 rounded-full mr-3"
                        style={{ backgroundColor: item.color }}
                      ></div>
                      <span className="text-sm text-gray-300">{item.label}</span>
                    </div>
                    <span className="text-xs text-gray-500">{item.range}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Real-time Theta Progression Chart */}
            {thetaProgression.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <h3 className="text-sm font-medium mb-4 text-gray-200">θ Progression</h3>
                <div className="h-28">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={thetaProgression}>
                      <XAxis
                        dataKey="question"
                        stroke="#9CA3AF"
                        fontSize={12}
                        label={{ value: '# Question', position: 'insideBottom', offset: -1, fill: '#9CA3AF' , fontsize: 9 }}
                      />
                      <YAxis
                        domain={[-2, 2]}
                        stroke="#9CA3AF"
                        fontSize={12}
                        label={{ value: 'θ', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                      />
                      <Tooltip
                        formatter={(value, name, props) => {
                          const isCorrect = props.payload?.correct;
                          return [
                            value,
                            `θ after ${isCorrect ? 'Correct ✅' : 'Incorrect ❌'} response`
                          ];
                        }}
                        labelFormatter={(label) => `Question ${label}`}
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '6px',
                          color: '#fff'
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="theta"
                        stroke="#6B7280"
                        strokeWidth={2}
                        dot={(props) => {
                          const { cx, cy, payload } = props;
                          if (!payload) return null;

                          // FIXED: Use proper boolean check
                          const isCorrect = Boolean(payload.correct);
                          const color = isCorrect ? '#22C55E' : '#EF4444';

                          // console.log(`Dot for Q${payload.question}: correct=${payload.correct} (${typeof payload.correct}) -> ${isCorrect} -> ${color}`);

                          return (
                            <circle
                              cx={cx}
                              cy={cy}
                              r={4}
                              fill={color}
                              stroke={color}
                              strokeWidth={1}
                            />
                          );
                        }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                {/* Legend */}
                <div className="flex justify-center space-x-4 mt-3">
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                    <span className="text-xs text-gray-400">Correct Response</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                    <span className="text-xs text-gray-400">Incorrect Response</span>
                  </div>
                </div>
              </div>
            )}

            {/* Difficulty Scatter Chart with REAL data */}
            {/*{difficultyData.length > 0 && (*/}
            {/*  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">*/}
            {/*    <h3 className="text-sm font-medium mb-4 text-gray-200">Response Pattern</h3>*/}
            {/*    <div className="h-28">*/}
            {/*      <ResponsiveContainer width="100%" height="100%">*/}
            {/*        <ScatterChart data={difficultyData}>*/}
            {/*          <XAxis*/}
            {/*            dataKey="x"*/}
            {/*            type="number"*/}
            {/*            domain={['dataMin - 0.1', 'dataMax + 0.1']}*/}
            {/*            ticks={[...new Set(difficultyData.map(item => item.x))].sort((a, b) => a - b)}*/}
            {/*            tickFormatter={(value) => value.toFixed(2)}*/}
            {/*            stroke="#9CA3AF"*/}
            {/*            fontSize={10}*/}
            {/*            label={{ value: 'Difficulty', position: 'insideBottom', offset: -3, fill: '#9CA3AF', fontSize: 12  }}*/}
            {/*          />*/}

            {/*          <YAxis*/}
            {/*            dataKey="y"*/}
            {/*            domain={[-2, 2]}*/}
            {/*            stroke="#9CA3AF"*/}
            {/*            fontSize={12}*/}
            {/*            label={{ value: 'θ', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}*/}
            {/*          />*/}

            {/*          console.log('Here value= ', value , ' and name = ', name);*/}
            {/*          <Tooltip*/}
            {/*            formatter={(value, name, props) => {*/}
            {/*              if (name === 'y') return [value, 'θ'];*/}

            {/*              return [value, name];*/}

            {/*            }}*/}
            {/*            labelFormatter={(_, payload) => {*/}
            {/*              if (payload && payload[0]) {*/}
            {/*                const data = payload[0].payload;*/}
            {/*                const isCorrect = Boolean(data.correct);*/}
            {/*                return `Question ${data.question} - ${isCorrect ? 'Correct  ✅ Response' : 'Incorrect ❌ Response'}`;*/}
            {/*              }*/}
            {/*              return '';*/}
            {/*            }}*/}
            {/*            contentStyle={{*/}
            {/*              backgroundColor: '#1f2937',*/}
            {/*              border: '1px solid #374151',*/}
            {/*              borderRadius: '6px',*/}
            {/*              color: '#fff'*/}
            {/*            }}*/}
            {/*          />*/}
            {/*          {(() => {*/}
            {/*            // FIXED: Use proper boolean check*/}


            {/*            // Debug the filtering before rendering*/}
            {/*            console.log(difficultyData.filter)*/}
            {/*            const correctData = difficultyData.filter(item => item.correct === true);*/}
            {/*            const incorrectData = difficultyData.filter(item => item.correct=== false);*/}

            {/*            console.log('🎨 Scatter Chart Rendering:', {*/}
            {/*              totalData: difficultyData.length,*/}
            {/*              correctCount: correctData.length,*/}
            {/*              incorrectCount: incorrectData.length,*/}
            {/*              correctItems: correctData.map(d => `Q${d.question}:${d.correct}`),*/}
            {/*              incorrectItems: incorrectData.map(d => `Q${d.question}:${d.correct}`)*/}
            {/*            });*/}

            {/*            return (*/}
            {/*              <>*/}
            {/*               /!* Use the SAME logic as θ Progression chart *!/*/}
            {/*                <Scatter*/}
            {/*                  dataKey="y"*/}
            {/*                  data={difficultyData}*/}
            {/*                  fill="#000"*/}
            {/*                  name="Responses"*/}
            {/*                >*/}
            {/*                  {difficultyData.map((entry, index) => {*/}
            {/*                    const isCorrect = Boolean(entry.correct);*/}
            {/*                    const color = isCorrect ? '#22C55E' : '#EF4444';*/}
            {/*                    return <Cell key={`cell-${index}`} fill={color} />;*/}
            {/*                  })}*/}
            {/*                </Scatter>*/}
            {/*              </>*/}
            {/*            );*/}
            {/*          })()}*/}
            {/*        </ScatterChart>*/}
            {/*      </ResponsiveContainer>*/}
            {/*    </div>*/}
            {/*    <div className="flex justify-center space-x-4 mt-2">*/}
            {/*      <div className="flex items-center">*/}
            {/*        <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>*/}
            {/*        <span className="text-xs text-gray-400">Correct Response</span>*/}
            {/*      </div>*/}
            {/*      <div className="flex items-center">*/}
            {/*        <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>*/}
            {/*        <span className="text-xs text-gray-400">Incorrect Response </span>*/}
            {/*      </div>*/}
            {/*    </div>*/}
            {/*  </div>*/}
            {/*)}*/}
            {/*  newly added*/}

            {/* ===== UPDATED SCATTER CHART RENDERING =====*/}
            {difficultyData.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h3 className="text-sm font-medium mb-4 text-gray-200">Response Pattern</h3>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart data={difficultyData}>
                      <XAxis
                        dataKey="x"
                        type="number"
                        domain={['dataMin - 0.1', 'dataMax + 0.1']}
                        ticks={[...new Set(difficultyData.map(item => item.x))].sort((a, b) => a - b)}
                        tickFormatter={(value) => value.toFixed(2)}
                        stroke="#9CA3AF"
                        fontSize={10}
                        label={{
                          value: 'Difficulty',
                          position: 'insideBottom',
                          offset: -10,
                          fill: '#9CA3AF',
                          fontSize: 10
                        }}
                      />
                      <YAxis
                        dataKey="y"
                        domain={[-2, 2]}
                        stroke="#9CA3AF"
                        fontSize={12}
                        label={{
                          value: 'θ',
                          angle: -90,
                          position: 'insideLeft',
                          fill: '#9CA3AF',
                          fontSize: 10
                        }}
                      />
                      <Tooltip
                        formatter={(value, name, props) => {
                          if (name === 'y') return [value, 'θ'];
                          return [value, name];
                        }}
                        labelFormatter={(_, payload) => {
                          if (payload && payload[0]) {
                            const data = payload[0].payload;
                            if (data.type === 'current') {
                              return `Question ${data.question} - Current Question (Unanswered)`;
                            } else {
                              const isCorrect = Boolean(data.correct);
                              return `Question ${data.question} - ${isCorrect ? 'Correct ✅' : 'Incorrect ❌'}`;
                            }
                          }
                          return '';
                        }}
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '6px',
                          color: '#fff'
                        }}
                      />

                      {/* Render all dots with conditional coloring */}
                      <Scatter
                        dataKey="y"
                        data={difficultyData}
                        fill="#000"
                        name="Responses"
                      >
                        {difficultyData.map((entry, index) => {
                          let color;
                          if (entry.type === 'current') {
                            // Gray for current unanswered question
                            color = '#6B7280';
                          } else {
                            // Green for correct, red for incorrect
                            color = entry.correct ? '#22C55E' : '#EF4444';
                          }
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>

                {/* Updated Legend */}
                <div className="flex justify-center space-x-4 mt-2">
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                    <span className="text-xs text-gray-400">Correct</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                    <span className="text-xs text-gray-400">Incorrect</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-gray-500 mr-2"></div>
                    <span className="text-xs text-gray-400">Current</span>
                  </div>
                </div>
              </div>
            )}


          </div>
        </div>
      </div>
    </div>
  );
};

export default AdaptiveAssessment;