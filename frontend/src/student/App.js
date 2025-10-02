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
  ComposedChart,
  ReferenceLine
} from 'recharts';
import './App.css';
import { DARK_MODE, theme } from '../config/theme';

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
  const [liveResponses, setLiveResponses] = useState([]);
  const [questionDifficulties, setQuestionDifficulties] = useState([]);
  const [currentQuestionDifficulty, setCurrentQuestionDifficulty] = useState(null);
  const [topicPerformance, setTopicPerformance] = useState({});

  const API_BASE = 'http://localhost:8000/api';
  const DEFAULT_COMPETENCE_LEVEL = 'beginner';

  // Professional color palette
  const tierColors = {
    'C1': '#DC2626',
    'C2': '#F59E0B',
    'C3': '#10B981',
    'C4': '#3B82F6'
  };

  // Chart colors based on theme
  const chartColors = {
    stroke: theme('#9CA3AF', '#9CA3AF'),
    line: '#3B82F6',
    referenceLine: '#3B82F6',
    tooltip: {
      bg: theme('#1F2937', '#FFFFFF'),
      border: theme('#374151', '#E5E7EB'),
      text: theme('#FFFFFF', '#000000')
    }
  };

  // Custom Tooltip for ICC Curve
  const ICCTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: chartColors.tooltip.bg,
            border: `1px solid ${chartColors.tooltip.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            color: chartColors.tooltip.text
          }}
        >
          <div style={{ marginBottom: '4px' }}>
            <span>θ: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.x.toFixed(2)}</span>
          </div>
          <div>
            <span>P(correct): </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.p.toFixed(3)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for Theta Progression
  const ThetaProgressionTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: chartColors.tooltip.bg,
            border: `1px solid ${chartColors.tooltip.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            color: chartColors.tooltip.text
          }}
        >
          <div style={{ marginBottom: '4px' }}>
            <span>Question #: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.question}</span>
          </div>
          <div>
            <span>θ: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.theta}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for Response Pattern
  const ResponsePatternTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: chartColors.tooltip.bg,
            border: `1px solid ${chartColors.tooltip.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            color: chartColors.tooltip.text
          }}
        >
          <div style={{ marginBottom: '4px' }}>
            <span>Question #: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.question}</span>
          </div>
          <div style={{ marginBottom: '4px' }}>
            <span>Difficulty: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.x.toFixed(2)}</span>
          </div>
          <div>
            <span>θ: </span>
            <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>{data.y.toFixed(2)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  const getDisplayTheta = () => {
    if (currentSession?.theta !== undefined) return currentSession.theta;
    if (userStats?.proficiencies?.length > 0) {
      const currentBankProficiency = userStats.proficiencies.find(
        p => p.item_bank === currentSession?.item_bank_name
      );
      if (currentBankProficiency) return currentBankProficiency.theta;
      return userStats.proficiencies[0]?.theta || 0.0;
    }
    return 0.0;
  };

  const generateICCData = useCallback((theta) => {
    const data = [];
    for (let x = -3; x <= 3; x += 0.1) {
      const p = 0.25 + (0.75) / (1 + Math.exp(-1.2 * (x - (theta || 0))));
      data.push({ x: parseFloat(x.toFixed(1)), p: parseFloat(p.toFixed(3)) });
    }
    return data;
  }, []);

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

  const handleApiError = (error, context) => {
    console.error(`Error in ${context}:`, error);
    setError(`Failed to ${context}. Please try again.`);
    setLoading(false);
  };

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

  const loadUserStats = async (username) => {
    try {
      const response = await fetch(`${API_BASE}/users/${username}/proficiency`);
      if (response.ok) {
        const stats = await response.json();
        setUserStats(stats);
      }
    } catch (error) {
      console.log('No previous stats found');
    }
  };

  const loadAvailableItemBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/item-banks`);
      if (response.ok) {
        const banks = await response.json();
        setAvailableItemBanks(banks);
      }
    } catch (error) {
      console.log('Failed to load item banks');
    }
  };

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
        setTopicPerformance({});
      } else {
        throw new Error('Failed to start assessment');
      }
    } catch (error) {
      handleApiError(error, 'start assessment');
    }
    setLoading(false);
  };

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

        // Update topic performance if available
        if (updatedSession.topic_performance) {
          setTopicPerformance(updatedSession.topic_performance);
        }

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
        const questionDifficulty = currentQuestion.difficulty_b || currentQuestion.difficulty || 0.0;
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

  const getCurrentThetaColor = (theta) => {
    if (theta < -1.0) return tierColors['C1'];
    if (theta < 0.0) return tierColors['C2'];
    if (theta < 1.0) return tierColors['C3'];
    return tierColors['C4'];
  };

  const getThetaTierLabel = (theta) => {
    if (theta < -1.0) return 'Beginner';
    if (theta < 0.0) return 'Intermediate';
    if (theta < 1.0) return 'Advanced';
    return 'Expert';
  };

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
      <div className={`min-h-screen ${theme('bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900', 'bg-gradient-to-br from-indigo-50 to-white')} flex items-center justify-center p-4`}>
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-100')} rounded-2xl shadow-xl p-8 w-full max-w-md border`}>
          <div className="text-center mb-8">
            <div className={`w-16 h-16 ${theme('bg-blue-600', 'bg-indigo-600')} rounded-xl flex items-center justify-center mx-auto mb-4`}>
              <span className="text-3xl text-white font-bold">θ</span>
            </div>
            <h1 className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-1`}>MyTheta</h1>
            <p className={`${theme('text-gray-400', 'text-gray-600')} text-sm`}>Adaptive Assessment Platform</p>
          </div>
          {error && (
            <div className={`mb-4 p-3 ${theme('bg-red-900/50 border-red-700 text-red-200', 'bg-red-50 border-red-200 text-red-700')} border rounded-lg text-sm`}>
              {error}
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label className={`block ${theme('text-gray-300', 'text-gray-700')} font-medium mb-2 text-sm`}>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && username.trim() && !loading && login()}
                className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-gray-50 border-gray-300 text-gray-900')} border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition`}
                placeholder="Enter your username"
                disabled={loading}
                autoFocus
              />
            </div>
            <button
              onClick={login}
              disabled={!username.trim() || loading}
              className={`w-full ${theme('bg-blue-600 hover:bg-blue-700', 'bg-indigo-600 hover:bg-indigo-700')} disabled:bg-gray-400 text-white rounded-lg px-4 py-3 font-semibold transition disabled:cursor-not-allowed`}
            >
              {loading ? 'Logging in...' : 'Continue'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const displayTheta = getDisplayTheta();
  const iccData = generateICCData(displayTheta);
  const thetaProgression = generateThetaProgression(liveResponses, results?.responses);
  const difficultyData = generateDifficultyData(
    liveResponses,
    currentQuestionDifficulty,
    currentSession?.theta,
    assessmentComplete
  );

  return (
    <div className={`min-h-screen ${theme('bg-gray-900', 'bg-gray-50')}`}>
      {/* Professional Header */}
      <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border-b sticky top-0 z-10 shadow-sm`}>
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 ${theme('bg-blue-600', 'bg-indigo-600')} rounded-lg flex items-center justify-center`}>
                <span className="text-xl text-white font-bold">θ</span>
              </div>
              <h1 className={`text-lg font-bold ${theme('text-white', 'text-gray-900')}`}>MyTheta</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>
                <span className={`font-medium ${theme('text-white', 'text-gray-900')}`}>{currentUser?.username}</span>
              </span>
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
                  setTopicPerformance({});
                }}
                className={`text-sm ${theme('text-gray-400 hover:text-white', 'text-gray-600 hover:text-gray-900')} font-medium transition`}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className={`${theme('bg-red-900/50 border-red-700', 'bg-red-50 border-red-200')} border-b px-6 py-3`}>
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <span className={`text-sm ${theme('text-red-200', 'text-red-700')}`}>{error}</span>
            <button onClick={() => setError(null)} className={`${theme('text-red-200', 'text-red-700')} font-bold`}>×</button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        {!currentSession ? (
          /* ASSESSMENT SELECTION */
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Choose Your Assessment</h2>
              <p className={theme('text-gray-400', 'text-gray-600')}>Select a subject to begin your adaptive test</p>
            </div>

            {userStats && userStats.proficiencies.length > 0 && (
              <div className={`mb-6 ${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50 border-blue-100')} border rounded-xl p-4`}>
                <h3 className={`text-sm font-semibold ${theme('text-blue-300', 'text-blue-900')} mb-3`}>Your Progress</h3>
                <div className="space-y-2">
                  {userStats.proficiencies.map(prof => (
                    <div key={prof.item_bank} className={`flex justify-between items-center ${theme('bg-gray-700/50', 'bg-white')} rounded-lg px-4 py-2.5 text-sm`}>
                      <span className={`font-semibold ${theme('text-white', 'text-gray-900')} capitalize`}>{prof.item_bank}</span>
                      <div className="flex items-center space-x-2">
                        <span
                          className="px-2.5 py-1 rounded-full text-xs font-bold text-white"
                          style={{ backgroundColor: getCurrentThetaColor(prof.theta) }}
                        >
                          {getThetaTierLabel(prof.theta)}
                        </span>
                        <span className={`${theme('text-gray-400', 'text-gray-500')} text-xs`}>θ = {prof.theta.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-3">
              {availableItemBanks.length > 0 ? (
                availableItemBanks.map((bank) => (
                  <button
                    key={bank.name}
                    onClick={() => startAssessment(bank.name)}
                    disabled={loading}
                    className={`w-full ${theme('bg-gray-800 hover:bg-gray-700 border-gray-700 hover:border-blue-600', 'bg-white hover:bg-gray-50 border-gray-200 hover:border-indigo-300')} border-2 rounded-xl px-6 py-4 transition text-left disabled:opacity-50`}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className={`font-bold ${theme('text-white', 'text-gray-900')} text-lg`}>{bank.display_name}</div>
                        <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mt-0.5`}>
                          {bank.total_items} questions • {bank.status}
                        </div>
                      </div>
                      <svg className={`w-5 h-5 ${theme('text-gray-500', 'text-gray-400')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                ))
              ) : (
                <div className={`text-center py-12 ${theme('text-gray-400', 'text-gray-500')}`}>
                  <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${theme('border-blue-500', 'border-indigo-600')} mx-auto mb-2`}></div>
                  Loading assessments...
                </div>
              )}
            </div>
          </div>
        ) : assessmentComplete ? (
          /* RESULTS PAGE */
          <div className="max-w-5xl mx-auto">
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-2xl shadow-sm border p-8 mb-6`}>
              <div className="text-center mb-8">
                <div className={`w-16 h-16 ${theme('bg-green-900/50', 'bg-green-100')} rounded-full flex items-center justify-center mx-auto mb-4`}>
                  <svg className={`w-8 h-8 ${theme('text-green-400', 'text-green-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Assessment Complete</h2>
                <p className={theme('text-gray-400', 'text-gray-600')}>Great job! Here are your results</p>
              </div>

              {results && (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className={`${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50 border-blue-100')} rounded-xl p-6 border`}>
                      <div className={`text-sm font-medium ${theme('text-blue-300', 'text-blue-700')} mb-1`}>Performance Level</div>
                      <div className={`text-3xl font-bold ${theme('text-blue-100', 'text-blue-900')} mb-1`}>{results.tier}</div>
                      <div className={`text-sm ${theme('text-blue-400', 'text-blue-600')}`}>{getThetaTierLabel(results.final_theta)}</div>
                    </div>

                    <div className={`${theme('bg-gray-700/50 border-gray-600', 'bg-gray-50 border-gray-200')} rounded-xl p-6 border`}>
                      <div className={`text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-3`}>Proficiency Levels</div>
                      <div className="space-y-1.5">
                        {[
                          { label: 'Beginner', color: tierColors.C1, range: 'θ < -1.0' },
                          { label: 'Intermediate', color: tierColors.C2, range: '-1.0 ≤ θ < 0.0' },
                          { label: 'Advanced', color: tierColors.C3, range: '0.0 ≤ θ < 1.0' },
                          { label: 'Expert', color: tierColors.C4, range: 'θ ≥ 1.0' }
                        ].map((item) => (
                          <div key={item.label} className="flex items-center justify-between text-xs">
                            <div className="flex items-center">
                              <div
                                className="w-2 h-2 rounded-full mr-2"
                                style={{ backgroundColor: item.color }}
                              ></div>
                              <span className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>{item.label}</span>
                            </div>
                            <span className={theme('text-gray-400', 'text-gray-500')}>{item.range}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className={`${theme('bg-gray-700/50', 'bg-gray-50')} rounded-xl p-4 mb-6 text-sm ${theme('text-gray-300', 'text-gray-700')}`}>
                    <div className="flex justify-around">
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Final θ:</span>{' '}
                        <span className="font-semibold">{results.final_theta?.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>SEM:</span>{' '}
                        <span className="font-semibold">{results.final_sem?.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Accuracy:</span>{' '}
                        <span className="font-semibold">{(results.accuracy * 100).toFixed(0)}%</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Questions:</span>{' '}
                        <span className="font-semibold">{results.questions_asked}</span>
                      </div>
                    </div>
                  </div>
                </>
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
                  setTopicPerformance({});
                }}
                className={`w-full ${theme('bg-blue-600 hover:bg-blue-700', 'bg-indigo-600 hover:bg-indigo-700')} text-white rounded-xl py-3 font-semibold transition`}
              >
                Take Another Assessment
              </button>
            </div>

            {/* All Charts Grid */}
            <div className="grid grid-cols-3 gap-6">
              {/* ICC Chart with vertical line and custom tooltip */}
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Item Characteristic Curve</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Probability of correct response</p>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={iccData}>
                      <XAxis
                        dataKey="x"
                        domain={[-3, 3]}
                        type="number"
                        fontSize={10}
                        stroke={chartColors.stroke}
                        label={{ value: 'Ability (θ)', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
                      />
                      <YAxis
                        domain={[0, 1]}
                        fontSize={10}
                        stroke={chartColors.stroke}
                        label={{ value: 'P(correct)', angle: -90, position: 'insideLeft', fontSize: 10, fill: chartColors.stroke }}
                      />
                      <Tooltip content={<ICCTooltip />} />
                      <ReferenceLine
                        x={displayTheta}
                        stroke={chartColors.referenceLine}
                        strokeWidth={2}
                        strokeDasharray="3 3"
                      />
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

                {/* Topic-wise theta beneath ICC */}
                {topicPerformance && Object.keys(topicPerformance).length > 0 && (
                  <div className="mt-4 space-y-2">
                    <h4 className={`text-xs font-semibold ${theme('text-gray-400', 'text-gray-700')} uppercase tracking-wide`}>Topic Performance</h4>
                    {Object.values(topicPerformance).map((perf) => (
                      <div key={perf.topic} className={`flex justify-between items-center text-xs ${theme('bg-gray-700/50', 'bg-gray-100')} rounded px-2.5 py-1.5`}>
                        <span className={`font-medium ${theme('text-gray-200', 'text-gray-900')} capitalize`}>{perf.topic}</span>
                        <span className={`font-semibold ${theme('text-gray-300', 'text-gray-700')}`}>θ = {perf.theta.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Theta Progression with custom tooltip */}
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>θ Progression</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Ability estimate over time</p>
                <div className="h-56">
                  {thetaProgression.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={thetaProgression}>
                        <XAxis
                          dataKey="question"
                          fontSize={10}
                          stroke={chartColors.stroke}
                          label={{ value: 'Question #', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
                        />
                        <YAxis
                          domain={[-2, 2]}
                          fontSize={10}
                          stroke={chartColors.stroke}
                          label={{ value: 'θ', angle: -90, position: 'insideLeft', fontSize: 10, fill: chartColors.stroke }}
                        />
                        <Tooltip content={<ThetaProgressionTooltip />} />
                        <Line
                          type="monotone"
                          dataKey="theta"
                          stroke="#3B82F6"
                          strokeWidth={2}
                          dot={false}
                        />
                        <Scatter dataKey="theta">
                          {thetaProgression.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.correct ? '#10B981' : '#EF4444'} />
                          ))}
                        </Scatter>
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className={`h-full flex items-center justify-center ${theme('text-gray-500', 'text-gray-400')} text-xs`}>
                      No data available
                    </div>
                  )}
                </div>
                <div className="mt-3 flex justify-center space-x-4 text-xs">
                  <div className="flex items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Correct</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Incorrect</span>
                  </div>
                </div>
              </div>

              {/* Response Pattern with enhanced custom tooltip */}
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Response Pattern</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Difficulty vs ability</p>
                <div className="h-56">
                  {difficultyData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart>
                        <XAxis
                          dataKey="x"
                          type="number"
                          fontSize={10}
                          stroke={chartColors.stroke}
                          label={{ value: 'Difficulty', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
                        />
                        <YAxis
                          domain={[-2, 2]}
                          fontSize={10}
                          stroke={chartColors.stroke}
                          label={{ value: 'θ', angle: -90, position: 'insideLeft', fontSize: 10, fill: chartColors.stroke }}
                        />
                        <Tooltip content={<ResponsePatternTooltip />} />
                        <Scatter data={difficultyData} dataKey="y">
                          {difficultyData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={entry.type === 'current' ? '#6B7280' : (entry.correct ? '#10B981' : '#EF4444')}
                            />
                          ))}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className={`h-full flex items-center justify-center ${theme('text-gray-500', 'text-gray-400')} text-xs`}>
                      No data available
                    </div>
                  )}
                </div>
                <div className="mt-3 flex justify-center space-x-3 text-xs">
                  <div className="flex items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Correct</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Incorrect</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : currentQuestion ? (
          /* TEST IN PROGRESS */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: ICC Chart with vertical line and custom tooltip */}
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
              <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Item Characteristic Curve</h3>
              <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Probability of correct response</p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={iccData}>
                    <XAxis
                      dataKey="x"
                      domain={[-3, 3]}
                      type="number"
                      fontSize={10}
                      stroke={chartColors.stroke}
                      label={{ value: 'Ability (θ)', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      fontSize={10}
                      stroke={chartColors.stroke}
                      label={{ value: 'P(correct)', angle: -90, position: 'insideLeft', fontSize: 10, fill: chartColors.stroke }}
                    />
                    <Tooltip content={<ICCTooltip />} />
                    <ReferenceLine
                      x={displayTheta}
                      stroke={chartColors.referenceLine}
                      strokeWidth={2}
                      strokeDasharray="3 3"
                    />
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

              {/* Topic-wise theta beneath ICC - real-time updates */}
              {topicPerformance && Object.keys(topicPerformance).length > 0 && (
                <div className="mt-4 space-y-2">
                  <h4 className={`text-xs font-semibold ${theme('text-gray-400', 'text-gray-700')} uppercase tracking-wide`}>Topic Performance</h4>
                  {Object.values(topicPerformance).map((perf) => (
                    <div key={perf.topic} className={`flex justify-between items-center text-xs ${theme('bg-gray-700/50', 'bg-gray-100')} rounded px-2.5 py-1.5`}>
                      <span className={`font-medium ${theme('text-gray-200', 'text-gray-900')} capitalize`}>{perf.topic}</span>
                      <span className={`font-semibold ${theme('text-gray-300', 'text-gray-700')}`}>θ = {perf.theta.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Center: Question */}
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-2xl shadow-sm border p-6`}>
              <div className="mb-6">
                <div className={`flex justify-between text-sm ${theme('text-gray-400', 'text-gray-600')} mb-2`}>
                  <span>Question {currentSession.questions_asked + 1}</span>
                  <span>SEM: {currentSession.sem?.toFixed(2)}</span>
                </div>
                <div className={`w-full ${theme('bg-gray-700', 'bg-gray-200')} rounded-full h-2`}>
                  <div
                    className={`h-2 rounded-full ${theme('bg-blue-600', 'bg-indigo-600')} transition-all duration-500`}
                    style={{ width: `${Math.min((currentSession.questions_asked / 20) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>

              <h2 className={`text-lg font-semibold ${theme('text-white', 'text-gray-900')} mb-5 leading-relaxed`}>
                {currentQuestion.question}
              </h2>

              <div className="space-y-2.5 mb-6">
                {[
                  { key: 'A', text: currentQuestion.option_a },
                  { key: 'B', text: currentQuestion.option_b },
                  { key: 'C', text: currentQuestion.option_c },
                  { key: 'D', text: currentQuestion.option_d }
                ].map((option) => (
                  <label
                    key={option.key}
                    className={`flex items-start p-3.5 rounded-xl border-2 cursor-pointer transition ${
                      selectedOption === option.key
                        ? theme('border-blue-500 bg-blue-900/20', 'border-indigo-500 bg-indigo-50')
                        : theme('border-gray-600 hover:border-gray-500 hover:bg-gray-700/50', 'border-gray-200 hover:border-gray-300 hover:bg-gray-50')
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
                    <div className={`w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      selectedOption === option.key ? theme('border-blue-500 bg-blue-500', 'border-indigo-500 bg-indigo-500') : theme('border-gray-500', 'border-gray-400')
                    }`}>
                      {selectedOption === option.key && (
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      )}
                    </div>
                    <div className="flex-1">
                      <span className={`font-semibold ${theme('text-gray-300', 'text-gray-700')} mr-2`}>{option.key}.</span>
                      <span className={`${theme('text-gray-200', 'text-gray-900')} text-sm`}>{option.text}</span>
                    </div>
                  </label>
                ))}
              </div>

              <div className="flex justify-between items-center">
                <button
                  onClick={() => setSelectedOption('')}
                  disabled={loading || !selectedOption}
                  className={`px-4 py-2 border-2 ${theme('border-gray-600 text-gray-300 hover:bg-gray-700', 'border-gray-300 text-gray-700 hover:bg-gray-50')} rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-medium transition text-sm`}
                >
                  Clear
                </button>
                <button
                  onClick={submitAnswer}
                  disabled={!selectedOption || loading}
                  className={`px-7 py-2 ${theme('bg-blue-600 hover:bg-blue-700', 'bg-indigo-600 hover:bg-indigo-700')} disabled:bg-gray-400 text-white rounded-lg font-semibold transition disabled:cursor-not-allowed text-sm`}
                >
                  {loading ? 'Submitting...' : 'Submit'}
                </button>
              </div>

              <div className={`mt-4 text-xs ${theme('text-gray-500', 'text-gray-500')} text-center`}>
                Press A, B, C, or D to select • Enter to submit
              </div>
            </div>

            {/* Right: Live Stats & Charts */}
            <div className="space-y-4">
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-1`}>Current θ</div>
                    <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>{displayTheta.toFixed(2)}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-1`}>Current Level</div>
                    <div
                      className="text-xl font-bold"
                      style={{ color: getCurrentThetaColor(displayTheta) }}
                    >
                      {getThetaTierLabel(displayTheta)}
                    </div>
                  </div>
                </div>
              </div>

              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <div className={`text-xs font-semibold ${theme('text-gray-400', 'text-gray-700')} mb-2 uppercase tracking-wide`}>Proficiency Levels</div>
                <div className="space-y-1.5">
                  {[
                    { label: 'Beginner', color: tierColors.C1, range: 'θ < -1.0' },
                    { label: 'Intermediate', color: tierColors.C2, range: '-1.0 ≤ θ < 0.0' },
                    { label: 'Advanced', color: tierColors.C3, range: '0.0 ≤ θ < 1.0' },
                    { label: 'Expert', color: tierColors.C4, range: 'θ ≥ 1.0' }
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between text-xs">
                      <div className="flex items-center">
                        <div
                          className="w-2 h-2 rounded-full mr-2"
                          style={{ backgroundColor: item.color }}
                        ></div>
                        <span className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>{item.label}</span>
                      </div>
                      <span className={theme('text-gray-400', 'text-gray-500')}>{item.range}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-2 text-sm`}>θ Progression</h3>
                <div className="h-40">
                  {thetaProgression.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={thetaProgression}>
                        <XAxis
                          dataKey="question"
                          fontSize={9}
                          stroke={chartColors.stroke}
                          label={{ value: 'Question #', position: 'insideBottom', offset: -5, fontSize: 9, fill: chartColors.stroke }}
                        />
                        <YAxis
                          domain={[-2, 2]}
                          fontSize={9}
                          stroke={chartColors.stroke}
                          label={{ value: 'θ', angle: -90, position: 'insideLeft', fontSize: 9, fill: chartColors.stroke }}
                        />
                        <Tooltip content={<ThetaProgressionTooltip />} />
                        <Line type="monotone" dataKey="theta" stroke="#3B82F6" strokeWidth={1.5} dot={false} />
                        <Scatter dataKey="theta">
                          {thetaProgression.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.correct ? '#10B981' : '#EF4444'} />
                          ))}
                        </Scatter>
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className={`h-full flex items-center justify-center ${theme('text-gray-500', 'text-gray-400')} text-xs`}>
                      Answer questions to see progression
                    </div>
                  )}
                </div>
                <div className="mt-2 flex justify-center space-x-3 text-xs">
                  <div className="flex items-center">
                    <div className="w-2 h-2 rounded-full bg-green-500 mr-1"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Correct</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 rounded-full bg-red-500 mr-1"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Incorrect</span>
                  </div>
                </div>
              </div>

              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-2 text-sm`}>Response Pattern</h3>
                <div className="h-40">
                  {difficultyData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart>
                        <XAxis
                          dataKey="x"
                          type="number"
                          fontSize={9}
                          stroke={chartColors.stroke}
                          label={{ value: 'Difficulty', position: 'insideBottom', offset: -5, fontSize: 9, fill: chartColors.stroke }}
                        />
                        <YAxis
                          domain={[-2, 2]}
                          fontSize={9}
                          stroke={chartColors.stroke}
                          label={{ value: 'θ', angle: -90, position: 'insideLeft', fontSize: 9, fill: chartColors.stroke }}
                        />
                        <Tooltip content={<ResponsePatternTooltip />} />
                        <Scatter data={difficultyData} dataKey="y">
                          {difficultyData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={entry.type === 'current' ? '#6B7280' : (entry.correct ? '#10B981' : '#EF4444')}
                            />
                          ))}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className={`h-full flex items-center justify-center ${theme('text-gray-500', 'text-gray-400')} text-xs`}>
                      Answer questions to see pattern
                    </div>
                  )}
                </div>
                <div className="mt-2 flex justify-center space-x-2 text-xs">
                  <div className="flex items-center">
                    <div className="w-2 h-2 rounded-full bg-green-500 mr-1"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Correct</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 rounded-full bg-red-500 mr-1"></div>
                    <span className={theme('text-gray-300', 'text-gray-600')}>Incorrect</span>
                  </div>
                  {!assessmentComplete && (
                    <div className="flex items-center">
                      <div className="w-2 h-2 rounded-full bg-gray-500 mr-1"></div>
                      <span className={theme('text-gray-300', 'text-gray-600')}>Current</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className={`text-center py-16 ${theme('text-gray-400', 'text-gray-500')}`}>
            <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${theme('border-blue-500', 'border-indigo-600')} mx-auto mb-4`}></div>
            <p>Loading question...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdaptiveAssessment;