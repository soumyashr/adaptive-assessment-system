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
  ComposedChart
} from 'recharts';
import './App.css';
import { theme } from '../config/theme';

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
  const [username, setUsername] = useState('');
  const [showLogin, setShowLogin] = useState(true);
  const [error, setError] = useState(null);
  const [availableItemBanks, setAvailableItemBanks] = useState([]);

  // Real-time tracking states
  const [liveResponses, setLiveResponses] = useState([]);
  const [questionDifficulties, setQuestionDifficulties] = useState([]);

  const API_BASE = 'http://localhost:8000/api';
  const [currentQuestionDifficulty, setCurrentQuestionDifficulty] = useState(null);

  // Default competence level
  const DEFAULT_COMPETENCE_LEVEL = 'beginner';

  // Tier color mapping
  const tierColors = {
    'C1': '#ef4444',
    'C2': '#f97316',
    'C3': '#eab308',
    'C4': '#22c55e'
  };

  const getDisplayTheta = () => {
    if (currentSession?.theta !== undefined) {
      return currentSession.theta;
    }
    if (userStats?.proficiencies?.length > 0) {
      const currentBankProficiency = userStats.proficiencies.find(
        p => p.item_bank === currentSession?.item_bank_name
      );
      if (currentBankProficiency) return currentBankProficiency.theta;

      return userStats.proficiencies[0]?.theta || 0.0;
    }
    return 0.0;
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

  // Generate real-time theta progression
  const generateThetaProgression = useCallback((liveData, finalData) => {
    const dataSource = assessmentComplete ? finalData : liveData;
    if (!dataSource || dataSource.length === 0) return [];

    return dataSource.map((resp, idx) => {
      const thetaValue = resp.theta_after || resp.theta || 0;
      const isCorrect = resp.is_correct !== undefined ? resp.is_correct : resp.correct;

      return {
        question: idx + 1,
        theta: parseFloat(thetaValue.toFixed(2)),
        correct: Boolean(isCorrect),
        difficulty: parseFloat((resp.difficulty || 0).toFixed(2))
      };
    });
  }, [assessmentComplete]);

  // Generate difficulty data
  const generateDifficultyData = useCallback((responses, currentDifficulty, currentTheta, isComplete) => {
    const scatterData = [];

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

    if (!isComplete && currentDifficulty !== null && currentTheta !== undefined) {
      scatterData.push({
        x: parseFloat((currentDifficulty).toFixed(2)),
        y: parseFloat(currentTheta.toFixed(2)),
        correct: null,
        question: responses.length + 1,
        type: 'current'
      });
    }
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
    if (!username.trim()) {
      setError('Please enter a username');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          initial_competence_level: DEFAULT_COMPETENCE_LEVEL
        })
      });

      if (response.ok) {
        const user = await response.json();
        setCurrentUser(user);
        setShowLogin(false);
        await loadUserStats(username.trim());
        await loadAvailableItemBanks();
      } else {
        throw new Error('Login failed');
      }
    } catch (error) {
      handleApiError(error, 'login');
    }
    setLoading(false);
  };

  // Load user statistics
  const loadUserStats = async (username) => {
    try {
      const response = await fetch(`${API_BASE}/users/${username}/proficiency`);
      if (response.ok) {
        const stats = await response.json();
        setUserStats(stats);
      }
    } catch (error) {
      console.log('No previous stats found for user');
    }
  };

  // Load available item banks
  const loadAvailableItemBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/item-banks`);
      if (response.ok) {
        const banks = await response.json();
        setAvailableItemBanks(banks);
      }
    } catch (error) {
      console.log('Failed to load item banks:', error);
    }
  };

  // Start assessment
  const startAssessment = async (subject = 'maths') => {
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

      if (response.ok) {
        const session = await response.json();
        setCurrentSession({ ...session, item_bank_name: subject });
        setCurrentQuestion(session.current_question);
        setAssessmentComplete(false);
        setResults(null);
        setLiveResponses([]);
        setQuestionDifficulties([]);
        setCurrentQuestionDifficulty(session.current_question?.difficulty_b || 0);
      } else {
        throw new Error('Failed to start assessment');
      }
    } catch (error) {
      handleApiError(error, 'start assessment');
    }
    setLoading(false);
  };

  // Submit answer
  const submitAnswer = async () => {
    if (!selectedOption || !currentSession || !currentQuestion) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/assessments/${currentSession.session_id}/answer?item_bank_name=${currentSession.item_bank_name}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: currentQuestion.id,
            selected_option: selectedOption
          })
        }
      );

      if (response.ok) {
        const updatedSession = await response.json();

        if (updatedSession.completed) {
          setCurrentSession({ ...updatedSession, item_bank_name: currentSession.item_bank_name });
          setAssessmentComplete(true);
          setCurrentQuestionDifficulty(null);
          setCurrentQuestion(null);

          try {
            await loadResults(updatedSession.session_id);
            await loadUserStats(currentUser.username);
          } catch (error) {
            console.error('Error loading results:', error);
          }

          setSelectedOption('');
          return;
        }

        let wasCorrect;
        if (updatedSession.last_response_correct !== undefined && updatedSession.last_response_correct !== null) {
          wasCorrect = Boolean(updatedSession.last_response_correct);
        } else {
          wasCorrect = String(selectedOption) === String(currentQuestion.correct_option);
        }

        const questionDifficulty = currentQuestion.difficulty_b ||
                                 currentQuestion.difficulty ||
                                 0.0;

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

        setLiveResponses(prev => [...prev, responseData]);
        setQuestionDifficulties(prev => [...prev, questionDifficulty]);
        setCurrentSession({ ...updatedSession, item_bank_name: currentSession.item_bank_name });
        setCurrentQuestion(updatedSession.current_question);
        setCurrentQuestionDifficulty(updatedSession.current_question?.difficulty_b || null);
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
      const response = await fetch(
        `${API_BASE}/assessments/${sessionId}/results?item_bank_name=${currentSession.item_bank_name}`
      );
      if (response.ok) {
        const resultsData = await response.json();
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

  // Reset loading when showing assessment selection
  useEffect(() => {
    if (!showLogin && !currentSession && !assessmentComplete) {
      setLoading(false);
    }
  }, [showLogin, currentSession, assessmentComplete]);

  // Login Screen
  if (showLogin) {
    return (
      <div className={`min-h-screen ${theme('bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900', 'bg-gradient-to-br from-blue-500 via-blue-600 to-purple-600')} flex items-center justify-center p-4`}>
        <div className={`${theme('bg-gray-800 border border-gray-700', 'bg-white')} rounded-2xl shadow-2xl p-8 w-full max-w-md`}>
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
              <span className="text-4xl text-white font-bold">θ</span>
            </div>
            <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>
              MyTheta Assessment
            </h1>
            <p className={theme('text-gray-400', 'text-gray-600')}>Adaptive testing platform</p>
          </div>

          {error && (
            <div className={`mb-4 p-4 ${theme('bg-red-900/50 border-red-700 text-red-200', 'bg-red-50 border-red-200 text-red-700')} border rounded-lg text-sm flex items-start`}>
              <svg className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className={`block ${theme('text-gray-300', 'text-gray-700')} font-semibold mb-2`}>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && username.trim() && !loading && login()}
                className={`w-full ${theme('bg-gray-700 border-gray-600 text-white', 'bg-white border-gray-300 text-gray-900')} border-2 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition`}
                placeholder="Enter your username"
                disabled={loading}
                autoFocus
              />
            </div>

            <button
              onClick={login}
              disabled={!username.trim() || loading}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-xl px-4 py-4 font-semibold transition shadow-lg hover:shadow-xl transform hover:scale-[1.02] disabled:transform-none disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Logging in...
                </div>
              ) : 'Start Assessment'}
            </button>

            <div className={`text-center text-xs ${theme('text-gray-400', 'text-gray-500')} mt-4 pt-4 ${theme('border-gray-700', 'border-gray-200')} border-t`}>
              <a href="/admin" className={`${theme('text-blue-400 hover:text-blue-300', 'text-blue-600 hover:text-blue-700')} font-medium`}>
                Admin Panel
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Generate chart data
  const displayTheta = getDisplayTheta();
  const iccData = generateICCData(displayTheta);
  const thetaProgression = generateThetaProgression(liveResponses, results?.responses);
  const difficultyData = generateDifficultyData(
    liveResponses,
    currentQuestionDifficulty,
    currentSession?.theta,
    assessmentComplete
  );

  // Chart color based on theme
  const chartColors = {
    stroke: theme('#9CA3AF', '#6B7280'),
    line: '#3B82F6',

    tooltip: {
      bg: theme('#1f2937', '#fff'),
      border: theme('#374151', '#E5E7EB')
    }
  };

  // Main Application
  return (
    <div className={`min-h-screen ${theme('bg-gray-900', 'bg-gray-50')}`}>
      {/* Header */}
      <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border-b shadow-sm sticky top-0 z-10`}>
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-md">
                <span className="text-2xl text-white font-bold">θ</span>
              </div>
              <div>
                <h1 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')}`}>MyTheta</h1>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')}`}>Student Assessment</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className={theme('text-gray-300', 'text-gray-700')}>
                <span className={theme('text-gray-400', 'text-gray-500')}>Welcome,</span> <span className="font-semibold">{currentUser?.username}</span>
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
                  setUsername('');
                  setSelectedOption('');
                  setLoading(false);
                  setError(null);
                  setUserStats(null);
                  setAvailableItemBanks([]);
                }}
                className={`${theme('text-gray-400 hover:text-white', 'text-gray-600 hover:text-gray-900')} text-sm font-medium transition`}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className={`${theme('bg-red-900/50 border-red-700', 'bg-red-50 border-red-200')} border-b px-6 py-3`}>
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <div className="flex items-center">
              <svg className={`w-5 h-5 ${theme('text-red-400', 'text-red-500')} mr-2`} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className={`${theme('text-red-200', 'text-red-700')} text-sm font-medium`}>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className={`${theme('text-red-200 hover:text-red-100', 'text-red-700 hover:text-red-900')} font-bold text-lg`}
            >
              ×
            </button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - ICC Chart */}
          <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-lg border p-6`}>
            <h3 className={`text-lg font-bold mb-2 ${theme('text-white', 'text-gray-900')}`}>Item Characteristic Curve</h3>
            <p className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mb-4`}>
              Probability of correct response across ability levels
            </p>
            <div className="h-48 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={iccData}>
                  <XAxis
                    dataKey="x"
                    domain={[-3, 3]}
                    type="number"
                    tickFormatter={(value) => value.toFixed(0)}
                    stroke={chartColors.stroke}
                    fontSize={11}
                    label={{ value: 'Ability (θ)', position: 'insideBottom', offset: -1, fill: chartColors.stroke, fontSize: 10 }}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tickFormatter={(value) => value.toFixed(1)}
                    stroke={chartColors.stroke}
                    fontSize={11}
                    label={{ value: 'Probability', angle: -90, position: 'outside', offset:10, fill: chartColors.stroke, fontSize: 10 }}
                  />
                  <Tooltip
                    formatter={(value) => [value.toFixed(3), 'Probability']}
                    labelFormatter={(label) => `θ: ${label}`}
                    contentStyle={{
                      backgroundColor: chartColors.tooltip.bg,
                      border: `1px solid ${chartColors.tooltip.border}`,
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      color: theme('#fff', '#000')
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p"
                    stroke={chartColors.line}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div>
              <h4 className={`text-sm font-bold mb-3 ${theme('text-white', 'text-gray-900')}`}>Current Proficiency</h4>
              <div className={`${theme('bg-gradient-to-br from-blue-900/50 to-purple-900/50 border-blue-700', 'bg-gradient-to-br from-blue-50 to-purple-50 border-blue-100')} rounded-xl p-4 border-2`}>
                <div className="flex justify-between items-center">
                  <span className={`${theme('text-white', 'text-gray-900')} capitalize font-semibold text-lg`}>
                    {currentSession?.item_bank_name || 'Assessment'}
                  </span>
                  <span
                    className="px-3 py-1 rounded-full text-xs font-bold text-white shadow-sm"
                    style={{ backgroundColor: getCurrentThetaColor(displayTheta) }}
                  >
                    {getThetaTierLabel(displayTheta)}
                  </span>
                </div>
                <div className={`mt-2 text-sm ${theme('text-gray-300', 'text-gray-700')} font-medium`}>
                  θ = {displayTheta.toFixed(2)}
                  {currentSession && `, SEM = ${currentSession.sem?.toFixed(2)}`}
                </div>
              </div>
            </div>
          </div>

          {/* Center Column - Assessment Interface */}
          <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-lg border p-8`}>
            {!currentSession ? (
              <div className="text-center">
                <div className="mb-8">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto shadow-lg mb-4">
                    <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h2 className={`text-2xl font-bold mb-4 ${theme('text-white', 'text-gray-900')}`}>Select Assessment</h2>
                  <p className={theme('text-gray-400', 'text-gray-600')}>
                    Choose an assessment that adapts to your ability
                  </p>
                </div>

                {userStats && userStats.proficiencies.length > 0 && (
                  <div className={`mb-8 p-5 ${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50 border-blue-100')} rounded-xl border-2`}>
                    <h3 className={`text-sm font-bold ${theme('text-blue-300', 'text-blue-900')} mb-3 uppercase tracking-wide`}>Your Previous Results</h3>
                    <div className="space-y-2">
                      {userStats.proficiencies.map(prof => (
                        <div key={prof.item_bank} className={`flex justify-between items-center text-sm ${theme('bg-gray-700/50', 'bg-white')} rounded-lg p-3`}>
                          <span className={`font-semibold ${theme('text-white', 'text-gray-900')} capitalize`}>{prof.item_bank}</span>
                          <span className={theme('text-gray-300', 'text-gray-600')}>
                            {getThetaTierLabel(prof.theta)} <span className={`text-xs ${theme('text-gray-400', 'text-gray-500')}`}>(θ={prof.theta.toFixed(2)})</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="space-y-4">
                  {availableItemBanks.length > 0 ? (
                    availableItemBanks.map((bank) => {
                      const gradientColors = {
                        'maths': 'from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700',
                        'mathematics': 'from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700',
                        'vocabulary': 'from-green-500 to-green-600 hover:from-green-600 hover:to-green-700',
                        'science': 'from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700',
                        'physics': 'from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700',
                        'chemistry': 'from-pink-500 to-pink-600 hover:from-pink-600 hover:to-pink-700',
                        'biology': 'from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700',
                        'default': 'from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700'
                      };

                      const gradient = gradientColors[bank.name.toLowerCase()] || gradientColors['default'];

                      return (
                        <button
                          key={bank.name}
                          onClick={() => startAssessment(bank.name)}
                          disabled={loading}
                          className={`w-full bg-gradient-to-r ${gradient} disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed text-white rounded-xl px-8 py-5 font-semibold transition shadow-lg hover:shadow-xl transform hover:scale-[1.02] disabled:transform-none`}
                        >
                          <div className="text-lg font-bold">{bank.display_name}</div>
                          <div className="text-sm opacity-90 mt-1">
                            {bank.total_items} questions • {bank.status}
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className={`${theme('text-gray-400', 'text-gray-500')} text-sm py-8`}>
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                      Loading assessments...
                    </div>
                  )}
                </div>
              </div>
            ) : assessmentComplete ? (
              <div className="text-center">
                <div className="mb-6">
                  <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-green-600 rounded-full flex items-center justify-center mx-auto shadow-lg">
                    <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
                <h2 className={`text-2xl font-bold mb-6 ${theme('text-white', 'text-gray-900')}`}>Assessment Complete!</h2>

                {results && (
                  <div className="mb-8">
                    <div className="grid grid-cols-2 gap-4">
                      <div className={`${theme('bg-gradient-to-br from-blue-900/50 to-blue-800/50 border-blue-700', 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200')} rounded-xl p-5 border-2`}>
                        <div className={`text-sm ${theme('text-blue-300', 'text-blue-700')} font-semibold uppercase tracking-wide`}>Final Level</div>
                        <div className={`text-2xl font-bold ${theme('text-white', 'text-blue-900')} mt-2`}>{results.tier}</div>
                      </div>
                      <div className={`${theme('bg-gradient-to-br from-green-900/50 to-green-800/50 border-green-700', 'bg-gradient-to-br from-green-50 to-green-100 border-green-200')} rounded-xl p-5 border-2`}>
                        <div className={`text-sm ${theme('text-green-300', 'text-green-700')} font-semibold uppercase tracking-wide`}>Accuracy</div>
                        <div className={`text-2xl font-bold ${theme('text-white', 'text-green-900')} mt-2`}>{(results.accuracy * 100).toFixed(1)}%</div>
                      </div>
                      <div className={`${theme('bg-gradient-to-br from-purple-900/50 to-purple-800/50 border-purple-700', 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200')} rounded-xl p-5 border-2`}>
                        <div className={`text-sm ${theme('text-purple-300', 'text-purple-700')} font-semibold uppercase tracking-wide`}>Questions</div>
                        <div className={`text-2xl font-bold ${theme('text-white', 'text-purple-900')} mt-2`}>{results.questions_asked}</div>
                      </div>
                      <div className={`${theme('bg-gradient-to-br from-orange-900/50 to-orange-800/50 border-orange-700', 'bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200')} rounded-xl p-5 border-2`}>
                        <div className={`text-sm ${theme('text-orange-300', 'text-orange-700')} font-semibold uppercase tracking-wide`}>Final θ</div>
                        <div className={`text-2xl font-bold ${theme('text-white', 'text-orange-900')} mt-2`}>{results.final_theta?.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={() => {
                    setAssessmentComplete(false);
                    setResults(null);
                    setCurrentSession(null);
                    setCurrentQuestion(null);
                    setLiveResponses([]);
                    setQuestionDifficulties([]);
                    setCurrentQuestionDifficulty(null);
                    setSelectedOption('');
                  }}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl px-8 py-4 font-semibold transition shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                >
                  Take Another Assessment
                </button>
              </div>
            ) : currentQuestion ? (
              <div>
                <div className="mb-8">
                  <div className={`flex justify-between text-sm ${theme('text-gray-400', 'text-gray-600')} mb-3`}>
                    <span className="font-semibold">Question {currentSession.questions_asked + 1}</span>
                    <span className="font-medium">θ: {currentSession.theta?.toFixed(2)} | SEM: {currentSession.sem?.toFixed(2)}</span>
                  </div>
                  <div className={`w-full ${theme('bg-gray-700', 'bg-gray-200')} rounded-full h-3 shadow-inner`}>
                    <div
                      className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-500 shadow-sm"
                      style={{
                        width: `${Math.min((currentSession.questions_asked / 20) * 100, 100)}%`
                      }}
                    ></div>
                  </div>
                </div>

                <div className="mb-8">
                  <h2 className={`text-xl font-semibold mb-6 ${theme('text-white', 'text-gray-900')} leading-relaxed`}>
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
                        className={`flex items-center p-5 rounded-xl border-2 cursor-pointer transition-all ${
                          selectedOption === option.key 
                            ? theme('border-blue-500 bg-blue-900/30 shadow-md scale-[1.02]', 'border-blue-500 bg-blue-50 shadow-md scale-[1.02]')
                            : theme('border-gray-600 hover:border-blue-500 hover:bg-gray-700/50 hover:shadow-sm', 'border-gray-300 hover:border-blue-300 hover:bg-gray-50 hover:shadow-sm')
                        }`}
                      >
                        <input
                          type="radio"
                          name="option"
                          value={option.key}
                          checked={selectedOption === option.key}
                          onChange={(e) => setSelectedOption(e.target.value)}
                          disabled={loading}
                          className="hidden"
                        />
                        <div className={`w-6 h-6 rounded-full border-2 mr-4 flex items-center justify-center flex-shrink-0 transition ${
                          selectedOption === option.key ? 'border-blue-500 bg-blue-500' : theme('border-gray-500', 'border-gray-400')
                        }`}>
                          {selectedOption === option.key && (
                            <div className="w-2.5 h-2.5 bg-white rounded-full"></div>
                          )}
                        </div>
                        <span className={`font-bold ${theme('text-gray-300', 'text-gray-700')} mr-3`}>{option.key}.</span>
                        <span className={theme('text-gray-200', 'text-gray-900')}>{option.text}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <button
                    onClick={() => setSelectedOption('')}
                    disabled={loading || !selectedOption}
                    className={`px-5 py-2.5 ${theme('border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-gray-500', 'border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400')} border-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-medium transition text-sm`}
                  >
                    Clear
                  </button>
                  <button
                    onClick={submitAnswer}
                    disabled={!selectedOption || loading}
                    className="px-8 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-lg font-medium transition shadow-md hover:shadow-lg transform hover:scale-[1.01] disabled:transform-none disabled:cursor-not-allowed text-sm"
                  >
                    {loading ? (
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting...
                      </div>
                    ) : 'Submit Answer'}
                  </button>
                </div>

                <div className={`mt-6 text-xs ${theme('text-gray-500', 'text-gray-500')} text-center font-medium`}>
                  Press A, B, C, or D to select • Enter to submit
                </div>
              </div>
            ) : (
              <div className={`text-center ${theme('text-gray-400', 'text-gray-500')} py-16`}>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="font-medium">Loading question...</p>
              </div>
            )}
          </div>

          {/* Right Column - Statistics & Charts */}
          <div className="space-y-4">
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-lg border p-4`}>
              <h3 className={`text-xs font-bold mb-3 ${theme('text-white', 'text-gray-900')} uppercase tracking-wide`}>Proficiency Levels</h3>
              <div className="space-y-2">
                {[
                  { label: 'Beginner', color: tierColors.C1, range: 'θ < -1.0' },
                  { label: 'Intermediate', color: tierColors.C2, range: '-1.0 ≤ θ < 0.0' },
                  { label: 'Advanced', color: tierColors.C3, range: '0.0 ≤ θ < 1.0' },
                  { label: 'Expert', color: tierColors.C4, range: 'θ ≥ 1.0' }
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div
                        className="w-3 h-3 rounded-full mr-2 shadow-sm"
                        style={{ backgroundColor: item.color }}
                      ></div>
                      <span className={`text-sm font-semibold ${theme('text-gray-200', 'text-gray-900')}`}>{item.label}</span>
                    </div>
                    <span className={`text-xs ${theme('text-gray-400', 'text-gray-500')} font-medium`}>{item.range}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-lg border p-4`}>
              <h3 className={`text-sm font-bold mb-3 ${theme('text-white', 'text-gray-900')}`}>θ Progression</h3>
              <div className="h-36 mb-2">
                {thetaProgression.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={thetaProgression}>
                      <XAxis
                        dataKey="question"
                        type="number"
                        domain={[1, 'dataMax']}
                        stroke={chartColors.stroke}
                        fontSize={10}
                        label={{
                          value: 'Question #',
                          position: 'insideBottom',
                          offset: -2,
                          fill: chartColors.stroke,
                          fontSize: 10
                        }}
                      />
                      <YAxis
                        domain={[-2, 2]}
                        stroke={chartColors.stroke}
                        fontSize={10}
                        label={{
                          value: 'θ',
                          angle: -90,
                          position: 'insideLeft',
                          fill: chartColors.stroke,
                          fontSize: 12
                        }}
                      />
                      <Tooltip
                        formatter={(value) => [value, 'θ']}
                        contentStyle={{
                          backgroundColor: chartColors.tooltip.bg,
                          border: `1px solid ${chartColors.tooltip.border}`,
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                          fontSize: '12px',
                          color: theme('#fff', '#000')
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="theta"
                        stroke={chartColors.line}
                        strokeWidth={1}
                        dot={false}
                      />
                      <Scatter dataKey="theta" fill="#000" name="Responses">
                        {thetaProgression.map((entry, index) => {
                          const color = entry.correct ? '#22C55E' : '#EF4444';
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Scatter>
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className={`h-full flex items-center justify-center ${theme('text-gray-400', 'text-gray-500')} text-xs font-medium`}>
                    Answer questions to see progression
                  </div>
                )}
              </div>
              <div className="flex justify-center space-x-4 mt-1">
                <div className="flex items-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5 shadow-sm"></div>
                  <span className={`text-xs ${theme('text-gray-300', 'text-gray-700')} font-medium`}>Correct</span>
                </div>
                <div className="flex items-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5 shadow-sm"></div>
                  <span className={`text-xs ${theme('text-gray-300', 'text-gray-700')} font-medium`}>Incorrect</span>
                </div>
              </div>
            </div>

            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-lg border p-4`}>
              <h3 className={`text-sm font-bold mb-3 ${theme('text-white', 'text-gray-900')}`}>Response Pattern</h3>
              <div className="h-36 mb-2">
                {difficultyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={difficultyData}>
                      <XAxis
                        dataKey="x"
                        type="number"
                        domain={['dataMin - 0.1', 'dataMax + 0.1']}
                        stroke={chartColors.stroke}
                        fontSize={10}
                        tickFormatter={(value) => value.toFixed(2)}
                        label={{
                          value: 'Difficulty',
                          position: 'insideBottom',
                          offset: -2,
                          fill: chartColors.stroke,
                          fontSize: 10
                        }}
                      />
                      <YAxis
                        domain={[-2, 2]}
                        stroke={chartColors.stroke}
                        fontSize={10}
                        label={{
                          value: 'θ',
                          angle: -90,
                          position: 'insideLeft',
                          fill: chartColors.stroke,
                          fontSize: 12
                        }}
                      />
                      <Tooltip
                        formatter={(value, name) => {
                          if (name === 'y') return [value.toFixed(2), 'θ'];
                          return [value, name];
                        }}
                        labelFormatter={(value) => `Difficulty: ${parseFloat(value).toFixed(2)}`}
                        contentStyle={{
                          backgroundColor: chartColors.tooltip.bg,
                          border: `1px solid ${chartColors.tooltip.border}`,
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                          fontSize: '12px',
                          color: theme('#fff', '#000')
                        }}
                      />
                      <Scatter dataKey="y" name="Responses">
                        {difficultyData.map((entry, index) => {
                          const color = entry.type === 'current' ? '#6B7280' : (entry.correct ? '#22C55E' : '#EF4444');
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Scatter>
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className={`h-full flex items-center justify-center ${theme('text-gray-400', 'text-gray-500')} text-xs font-medium`}>
                    Answer questions to see pattern
                  </div>
                )}
              </div>
              <div className="flex justify-center space-x-3 mt-1">
                <div className="flex items-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5 shadow-sm"></div>
                  <span className={`text-xs ${theme('text-gray-300', 'text-gray-700')} font-medium`}>Correct</span>
                </div>
                <div className="flex items-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5 shadow-sm"></div>
                  <span className={`text-xs ${theme('text-gray-300', 'text-gray-700')} font-medium`}>Incorrect</span>
                </div>
                {!assessmentComplete && (
                  <div className="flex items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-gray-500 mr-1.5 shadow-sm"></div>
                    <span className={`text-xs ${theme('text-gray-300', 'text-gray-700')} font-medium`}>Current</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdaptiveAssessment;