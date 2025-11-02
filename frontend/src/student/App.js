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
  ReferenceLine,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend
} from 'recharts';
import './App.css';
import { DARK_MODE, theme, toggleDarkMode } from '../config/theme';
import config from '../config/config';
import StudentDashboard from './pages/StudentDashboard';
import notificationService from '../services/notificationService';

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
  const [isDarkMode, setIsDarkMode] = useState(DARK_MODE); // Sync with theme.js

  // NEW: Track tier information from backend
  const [currentTierInfo, setCurrentTierInfo] = useState({
    estimated_tier: null,
    active_tier: null,
    tier_aligned: true,
    tier_note: ''
  });

  const [precisionQuality, setPrecisionQuality] = useState(null);
  const [progressToTarget, setProgressToTarget] = useState(null);
  const [targetSem, setTargetSem] = useState(0.3); // Default for formative

  const API_BASE = config.API_BASE_URL;
  const DEFAULT_COMPETENCE_LEVEL = 'beginner';

  // Handle theme toggle using the theme.js function
  const handleToggleDarkMode = () => {
    const newMode = toggleDarkMode(); // Use the function from theme.js
    setIsDarkMode(newMode); // Update local state to trigger re-render
  };

  // Listen for theme changes from other sources
  useEffect(() => {
    const handleThemeChange = () => {
      setIsDarkMode(DARK_MODE); // Sync with theme.js DARK_MODE
    };

    window.addEventListener('themeChange', handleThemeChange);

    // Initialize on mount
    setIsDarkMode(DARK_MODE);

    return () => {
      window.removeEventListener('themeChange', handleThemeChange);
    };
  }, []);

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

  // Export PDF function
  const handleExportPDF = async () => {
    if (!currentSession?.session_id || !results) {
      notificationService.notify('No session data available to export');
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/sessions/${currentSession.session_id}/export-pdf?item_bank_name=${currentSession.item_bank_name}`
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `assessment_report_${currentSession.item_bank_name}_${currentSession.session_id}_${currentUser.username}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        notificationService.error('Failed to export session report');
        console.error('Export failed with status:', response.status);
      }
    } catch (error) {
      console.error('Error exporting session:', error);
      notificationService.error('Error exporting session report');
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
        console.log('Available item banks:', banks);
        setAvailableItemBanks(banks);
      }
    } catch (error) {
      console.log('Failed to load item banks');
    }
  };

  // ========== COMPONENT: Learning Roadmap ==========
  const LearningRoadmap = ({ results, theme }) => {
    const topicPerformance = results?.topic_performance || {};
    const roadmap = results?.learning_roadmap;

    if (!topicPerformance || Object.keys(topicPerformance).length === 0) {
      return null;
    }

    const topics = Object.values(topicPerformance);

    const strengthColors = {
      'Strong': { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' },
      'Proficient': { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
      'Developing': { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' },
      'Needs Practice': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' }
    };

    const getStrengthColor = (level) => strengthColors[level] || strengthColors['Developing'];

    return (
      <div className="space-y-6 mt-6">
        {/* Overall Assessment */}
        {roadmap?.overall_message && (
          <div className={`${theme('bg-blue-800/90 border-blue-600', 'bg-blue-200 border-blue-400')} border rounded-xl p-5`}>
            <div className="flex items-start space-x-3">
              <div className={`${theme('bg-blue-600', 'bg-blue-600')} rounded-full p-2 flex-shrink-0`}>
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1`}>Overall Assessment</h3>
                <p className={`text-sm ${theme('text-gray-200', 'text-gray-900')}`}>{roadmap.overall_message}</p>
              </div>
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-4">
          <div className={`${theme('bg-green-800/90 border-green-600', 'bg-green-200 border-green-400')} border rounded-xl p-4 text-center`}>
            <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>
              {roadmap?.strengths?.length || 0}
            </div>
            <div className={`text-xs ${theme('text-green-100', 'text-gray-900')} mt-1 font-bold`}>Strong Topics</div>
          </div>

          <div className={`${theme('bg-yellow-700/90 border-yellow-600', 'bg-yellow-200 border-yellow-400')} border rounded-xl p-4 text-center`}>
            <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>
              {roadmap?.weaknesses?.length || 0}
            </div>
            <div className={`text-xs ${theme('text-yellow-100', 'text-gray-900')} mt-1 font-bold`}>Focus Areas</div>
          </div>

          <div className={`${theme('bg-blue-800/90 border-blue-600', 'bg-blue-200 border-blue-400')} border rounded-xl p-4 text-center`}>
            <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>
              {topics.length}
            </div>
            <div className={`text-xs ${theme('text-blue-100', 'text-gray-900')} mt-1 font-bold`}>Topics Assessed</div>
          </div>
        </div>

        {/* Your Learning Roadmap Section */}
        {roadmap?.recommendations && roadmap.recommendations.length > 0 && (
          <div>
            <h3 className={`font-bold ${theme('text-white', 'text-gray-900')} mb-4 text-lg`}>Your Learning Roadmap</h3>
            <div className="space-y-4">
              {/* Next Milestone */}
              {roadmap?.next_milestone && (
                <div className={`${theme('bg-gradient-to-r from-purple-800/90 to-blue-800/90 border-purple-600', 'bg-gradient-to-r from-purple-200 to-blue-200 border-purple-400')} border rounded-xl p-5`}>
                  <div className="flex items-start space-x-3">
                    <div className={`${theme('bg-purple-600', 'bg-purple-600')} rounded-full p-2 flex-shrink-0`}>
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h4 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-2`}>Next Milestone</h4>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className={`${theme('text-purple-200', 'text-gray-900')} block text-xs mb-0.5 font-bold`}>Target Level</span>
                          <span className={`font-bold ${theme('text-white', 'text-gray-900')}`}>{roadmap.next_milestone.target_tier}</span>
                        </div>
                        <div>
                          <span className={`${theme('text-purple-200', 'text-gray-900')} block text-xs mb-0.5 font-bold`}>Target θ</span>
                          <span className={`font-bold ${theme('text-white', 'text-gray-900')}`}>{roadmap.next_milestone.target_theta.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className={`${theme('text-purple-200', 'text-gray-900')} block text-xs mb-0.5 font-bold`}>Est. Questions</span>
                          <span className={`font-bold ${theme('text-white', 'text-gray-900')}`}>{roadmap.next_milestone.estimated_questions}</span>
                        </div>
                        <div>
                          <span className={`${theme('text-purple-200', 'text-gray-900')} block text-xs mb-0.5 font-bold`}>Focus Area</span>
                          <span className={`font-bold ${theme('text-white', 'text-gray-900')} text-xs`}>{roadmap.next_milestone.focus}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {roadmap.recommendations.map((rec, index) => {
                const iconMap = {
                  'immediate_focus': { icon: '🎯', color: 'red' },
                  'practice_more': { icon: '📚', color: 'yellow' },
                  'maintain': { icon: '✅', color: 'green' }
                };
                const recStyle = iconMap[rec.type] || iconMap['practice_more'];

                return (
                  <div
                    key={index}
                    className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-5`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="text-2xl flex-shrink-0">{recStyle.icon}</div>
                      <div className="flex-1">
                        <h4 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1`}>{rec.title}</h4>
                        <p className={`text-sm ${theme('text-gray-300', 'text-gray-700')} mb-2`}>{rec.description}</p>

                        {rec.topics && rec.topics.length > 0 && (
                          <div className="mb-2">
                            <div className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mb-1 font-medium`}>Topics:</div>
                            <div className="flex flex-wrap gap-1.5">
                              {rec.topics.map((topic, idx) => (
                                <span
                                  key={idx}
                                  className={`px-2.5 py-1 ${theme('bg-gray-700', 'bg-gray-100')} rounded-md text-xs font-medium ${theme('text-gray-200', 'text-gray-700')} capitalize`}
                                >
                                  {topic}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {rec.action && (
                          <div className={`text-xs ${theme('text-blue-400', 'text-blue-600')} font-medium mt-2`}>
                            💡 {rec.action}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Topic-wise Performance with Radar chart */}
        <div>
          <h3 className={`font-bold ${theme('text-white', 'text-gray-900')} mb-4 text-lg`}>Topic-wise Performance</h3>

          {/* Radar Chart */}
          {topics.length > 0 && (
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-6 mb-6`}>
              <h4 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-4 text-base`}>Performance Overview</h4>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={topics.map(topic => ({
                    topic: topic.topic.charAt(0).toUpperCase() + topic.topic.slice(1),
                    accuracy: topic.accuracy * 100,
                    theta: ((topic.theta + 3) / 6) * 100,
                  }))}>
                    <PolarGrid stroke={theme('#374151', '#E5E7EB')} />
                    <PolarAngleAxis
                      dataKey="topic"
                      tick={{ fill: theme('#D1D5DB', '#6B7280'), fontSize: 12 }}
                    />
                    <PolarRadiusAxis
                      angle={90}
                      domain={[0, 100]}
                      tick={{ fill: theme('#9CA3AF', '#9CA3AF'), fontSize: 10 }}
                    />
                    <Radar
                      name="Accuracy %"
                      dataKey="accuracy"
                      stroke="#10B981"
                      fill="#10B981"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                    <Radar
                      name="Proficiency (normalized)"
                      dataKey="theta"
                      stroke="#3B82F6"
                      fill="#3B82F6"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                    <Legend
                      wrapperStyle={{
                        fontSize: '12px',
                        color: theme('#D1D5DB', '#6B7280')
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: theme('#1F2937', '#FFFFFF'),
                        border: `1px solid ${theme('#374151', '#E5E7EB')}`,
                        borderRadius: '8px',
                        fontSize: '11px',
                        color: theme('#FFFFFF', '#000000')
                      }}
                      formatter={(value, name) => {
                        if (name === 'Proficiency (normalized)') {
                          const originalTheta = (value / 100) * 6 - 3;
                          return [originalTheta.toFixed(2), 'θ'];
                        }
                        return [value.toFixed(1) + '%', name];
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topics.map((topic) => {
              const colors = getStrengthColor(topic.strength_level);
              return (
                <div
                  key={topic.topic}
                  className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-4 hover:shadow-md transition`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className={`font-semibold ${theme('text-white', 'text-gray-900')} capitalize text-base`}>
                        {topic.topic}
                      </h4>
                      <div className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mt-1`}>
                        {topic.questions_answered} question{topic.questions_answered !== 1 ? 's' : ''} answered
                      </div>
                    </div>
                    <span className={`px-3 py-1 ${colors.bg} ${colors.text} ${colors.border} border rounded-full text-xs font-bold`}>
                      {topic.strength_level}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>Proficiency (θ)</span>
                      <span className={`font-bold ${theme('text-blue-400', 'text-blue-600')}`}>{topic.theta.toFixed(2)}</span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>Accuracy</span>
                      <span className={`font-bold ${theme('text-white', 'text-gray-900')}`}>
                        {(topic.accuracy * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>Correct</span>
                      <span className={`font-semibold ${theme('text-gray-300', 'text-gray-700')}`}>
                        {topic.correct_count}/{topic.questions_answered}
                      </span>
                    </div>

                    <div className={`w-full ${theme('bg-gray-700', 'bg-gray-200')} rounded-full h-2 mt-2`}>
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          topic.accuracy >= 0.8 ? 'bg-green-500' :
                          topic.accuracy >= 0.6 ? 'bg-blue-500' :
                          topic.accuracy >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${topic.accuracy * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };
  // ========== END Learning Roadmap ==========

  const startAssessment = async (subject = 'maths') => {
    setLoading(true);
    setError(null);

    // NEW: Reset tier info for new assessment
    setCurrentTierInfo({
      estimated_tier: null,
      active_tier: null,
      tier_aligned: true,
      tier_note: ''
    });

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
        console.log('start_Assessment() session.current_question:', session.current_question);
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

        // NEW: Capture tier information from backend response
        if (updatedSession.estimated_tier && updatedSession.active_tier) {
          setCurrentTierInfo({
            estimated_tier: updatedSession.estimated_tier,
            active_tier: updatedSession.active_tier,
            tier_aligned: updatedSession.tier_alignment || (updatedSession.estimated_tier === updatedSession.active_tier),
            tier_note: updatedSession.tier_note || ''
          });
          setPrecisionQuality(null);
          setProgressToTarget(null);
        }

        if (updatedSession.precision_quality) {
          setPrecisionQuality(updatedSession.precision_quality);
        }
        if (updatedSession.progress_to_target !== undefined) {
          setProgressToTarget(updatedSession.progress_to_target);
        }
        if (updatedSession.target_sem !== undefined) {
          setTargetSem(updatedSession.target_sem);
        }

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

        // NEW: Capture final tier information
        if (resultsData.estimated_tier && resultsData.active_tier) {
          setCurrentTierInfo({
            estimated_tier: resultsData.estimated_tier,
            active_tier: resultsData.active_tier,
            tier_aligned: resultsData.estimated_tier === resultsData.active_tier,
            tier_note: resultsData.tier_note || ''
          });
        }

        // NEW: Capture final precision information
        if (resultsData.precision_quality) {
          setPrecisionQuality(resultsData.precision_quality);
        }
        if (resultsData.progress_to_target !== undefined) {
          setProgressToTarget(resultsData.progress_to_target);
        }
        if (resultsData.target_sem !== undefined) {
          setTargetSem(resultsData.target_sem);
        }

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

  // NEW: Helper functions for tier code mapping
  const getTierLabel = (tierCode) => {
    const tierMap = {
      'C1': 'Beginner',
      'C2': 'Intermediate',
      'C3': 'Advanced',
      'C4': 'Expert'
    };
    return tierMap[tierCode] || 'Unknown';
  };

  const getTierColor = (tierCode) => {
    return tierColors[tierCode] || '#9CA3AF';
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
        {/* Dark Mode Toggle - Fixed Position */}
        <button
          onClick={handleToggleDarkMode}
          className={`fixed top-6 right-6 p-3 rounded-lg transition shadow-lg ${theme('bg-gray-800 hover:bg-gray-700 text-yellow-400 border border-gray-700', 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200')}`}
          aria-label="Toggle dark mode"
        >
          {isDarkMode ? (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fillRule="evenodd" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
            </svg>
          )}
        </button>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-100')} rounded-2xl shadow-xl p-8 w-full max-w-md border`}>
          <div className="text-center mb-8">
            <div className={`w-16 h-16 ${theme('bg-green-600', 'bg-green-600')} rounded-xl flex items-center justify-center mx-auto mb-4`}>
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
              className={`w-full ${theme('bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600', 'bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600')} disabled:bg-gray-400 text-white rounded-lg px-4 py-3 font-semibold transition disabled:cursor-not-allowed`}
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
      {/* Professional Header with Dark Mode Toggle */}
      <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border-b sticky top-0 z-10 shadow-sm`}>
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 ${theme('bg-green-600', 'bg-green-600')} rounded-lg flex items-center justify-center`}>
                <span className="text-xl text-white font-bold">θ</span>
              </div>
              <h1 className={`text-lg font-bold ${theme('text-white', 'text-gray-900')}`}>MyTheta</h1>
            </div>
            <div className="flex items-center space-x-4">
              {/* Dark Mode Toggle Button */}
              <button
                onClick={handleToggleDarkMode}
                className={`p-2 rounded-lg transition ${theme('bg-gray-700 hover:bg-gray-600 text-yellow-400', 'bg-gray-100 hover:bg-gray-200 text-gray-700')}`}
                aria-label="Toggle dark mode"
              >
                {isDarkMode ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fillRule="evenodd" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
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
          /* STUDENT DASHBOARD */
          <StudentDashboard
            userStats={userStats}
            availableItemBanks={availableItemBanks}
            onStartAssessment={startAssessment}
            loading={loading}
          />
        ) : assessmentComplete ? (
          /* RESULTS PAGE */
          <div className="max-w-5xl mx-auto">
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-2xl shadow-sm border p-8 mb-6`}>
              <div className="flex justify-between items-start mb-6">
                <div className="text-center flex-1">
                  <div className={`w-16 h-16 ${theme('bg-green-600', 'bg-green-600')} rounded-full flex items-center justify-center mx-auto mb-4`}>
                    <svg className={`w-8 h-8 ${theme('text-white', 'text-white')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h2 className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Assessment Complete</h2>
                  <p className={theme('text-gray-400', 'text-gray-600')}>Great job! Here are your results</p>
                </div>
                <button
                  onClick={handleExportPDF}
                  className={`px-4 py-2 ${theme('bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600', 'bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600')} text-white rounded-lg flex items-center gap-2 transition`}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 10h6m-6 4h10" />
                  </svg>
                  Export PDF
                </button>
              </div>

              {results && (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className={`${theme('bg-gradient-to-br from-yellow-900/40 via-green-900/30 to-teal-900/40 border-yellow-700/50', 'bg-gradient-to-br from-yellow-50 via-green-50 to-teal-50 border-yellow-200')} rounded-xl p-6 border`}>
                      <div className={`text-sm font-medium ${theme('text-yellow-300', 'text-yellow-700')} mb-1`}>Performance Level</div>
                      <div className={`text-3xl font-bold ${theme('text-yellow-100', 'text-yellow-900')} mb-1`}>{results.tier}</div>
                      <div className={`text-sm ${theme('text-green-400', 'text-green-700')}`}>{getThetaTierLabel(results.final_theta)}</div>
                    </div>

                    <div className={`${theme('bg-gradient-to-br from-green-900/40 via-teal-900/30 to-cyan-900/40 border-green-700/50', 'bg-gradient-to-br from-green-50 via-teal-50 to-cyan-50 border-green-200')} rounded-xl p-6 border`}>
                      <div className={`text-sm font-medium ${theme('text-green-300', 'text-green-700')} mb-3`}>Proficiency Levels</div>
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

                  {/* Precision Quality on Results Page */}
                  {results.precision_quality && (
                    <div className={`${theme('bg-gradient-to-br from-blue-900/40 via-cyan-900/30 to-teal-900/40 border-blue-700/50', 'bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 border-blue-200')} rounded-xl p-6 border mb-6`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className={`text-sm font-medium ${theme('text-blue-300', 'text-blue-700')} mb-2`}>
                            Measurement Quality
                          </div>
                          <div
                            className="text-2xl font-bold mb-1"
                            style={{ color: results.precision_quality.color }}
                          >
                            {results.precision_quality.label}
                          </div>
                          <div className={`text-xs ${theme('text-gray-400', 'text-gray-600')}`}>
                            Final SEM: {results.final_sem?.toFixed(3)} • Target: {targetSem?.toFixed(1) || '0.3'}
                          </div>
                        </div>

                        {/* Star Rating */}
                        <div className="flex gap-1">
                          {[1, 2, 3, 4, 5].map(star => (
                            <svg
                              key={star}
                              className="w-6 h-6"
                              fill={star <= results.precision_quality.stars ? results.precision_quality.color : '#4B5563'}
                              viewBox="0 0 20 20"
                            >
                              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                          ))}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      {results.progress_to_target !== null && results.progress_to_target !== undefined && (
                        <div className="mt-4">
                          <div className="flex justify-between text-xs mb-2">
                            <span className={theme('text-blue-300', 'text-blue-700')}>
                              Progress to Target
                            </span>
                            <span className={theme('text-blue-200', 'text-blue-800')} className="font-semibold">
                              {Math.round(results.progress_to_target * 100)}%
                            </span>
                          </div>
                          <div className={`w-full h-2 ${theme('bg-gray-700', 'bg-gray-200')} rounded-full overflow-hidden`}>
                            <div
                              className="h-full transition-all duration-500 rounded-full"
                              style={{
                                width: `${Math.min(results.progress_to_target * 100, 100)}%`,
                                backgroundColor: results.precision_quality.color
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )}
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
                  setLoading(false);
                }}
                className={`w-full ${theme('bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600', 'bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600')} text-white rounded-xl py-3 font-semibold transition`}
              >
                Take Another Assessment
              </button>
            </div>

            {/* All Charts Grid */}
            <div className="grid grid-cols-3 gap-6 mb-6">
              {/* ICC Chart */}
              <div className={`${theme('bg-gradient-to-br from-gray-800 to-gray-800/95 border-yellow-900/30', 'bg-gradient-to-br from-yellow-50/50 to-green-50/30 border-yellow-200/50')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Item Characteristic Curve</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Probability of correct response versus Proficiency(θ)</p>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={iccData}>
                      <XAxis
                        dataKey="x"
                        domain={[-3, 3]}
                        type="number"
                        fontSize={10}
                        stroke={chartColors.stroke}
                        label={{ value: 'Proficiency (θ)', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
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
              </div>

              {/* Theta Progression */}
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Proficiency(θ) Progression</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Proficiency estimate over time</p>
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

              {/* Response Pattern */}
              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Response Pattern</h3>
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Difficulty vs Proficiency</p>
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

            {/* Learning Roadmap */}
            <LearningRoadmap results={results} theme={theme} />
          </div>
        ) : currentQuestion ? (
          /* TEST IN PROGRESS */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: ICC Chart */}
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-5`}>
              <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Item Characteristic Curve</h3>
              <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-3`}>Probability of correct response versus proficiency(θ)</p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={iccData}>
                    <XAxis
                      dataKey="x"
                      domain={[-3, 3]}
                      type="number"
                      fontSize={10}
                      stroke={chartColors.stroke}
                      label={{ value: 'Proficiency (θ)', position: 'insideBottom', offset: -5, fontSize: 10, fill: chartColors.stroke }}
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

            {/* Center: Question */}
            <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-2xl shadow-sm border p-6`}>
              <div className="mb-6">
                <div className={`flex justify-between text-sm ${theme('text-gray-400', 'text-gray-600')} mb-2`}>
                  <span>Question {currentSession.questions_asked + 1}</span>
                  <span>SEM: {currentSession.sem?.toFixed(2)}</span>
                </div>
                <div className={`w-full ${theme('bg-gray-700', 'bg-gray-200')} rounded-full h-2`}>
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-yellow-400 to-green-500 transition-all duration-500"
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
                        ? theme('border-green-500 bg-green-900/20', 'border-green-500 bg-green-50')
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
                      selectedOption === option.key 
                        ? theme('border-green-500 bg-green-500', 'border-green-500 bg-green-500') 
                        : theme('border-gray-500', 'border-gray-400')
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
                  className={`px-7 py-2 ${theme('bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600', 'bg-gradient-to-r from-yellow-400 via-green-500 to-teal-500 hover:from-yellow-500 hover:via-green-600 hover:to-teal-600')} disabled:bg-gray-400 text-white rounded-lg font-semibold transition disabled:cursor-not-allowed text-sm`}
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
                    <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-1`}>Current Proficiency (θ)</div>
                    <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>{displayTheta.toFixed(2)}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-1 flex items-center gap-1 justify-end`}>
                      Question Level
                      {/* Info icon - shows when tiers don't align */}
                      {!currentTierInfo.tier_aligned && currentTierInfo.tier_note && (
                        <div className="relative group">
                          <svg
                            className={`w-3.5 h-3.5 ${theme('text-blue-400', 'text-blue-500')} cursor-help`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                              clipRule="evenodd"
                            />
                          </svg>
                          {/* Tooltip */}
                          <div className={`absolute right-0 bottom-full mb-2 w-56 p-2 rounded-lg text-xs ${theme('bg-gray-700 text-gray-200 border border-gray-600', 'bg-white text-gray-700 border border-gray-200 shadow-lg')} hidden group-hover:block z-50`}>
                            <div className="font-semibold mb-1">Why different levels?</div>
                            <div className={theme('text-gray-300', 'text-gray-600')}>
                              {currentTierInfo.tier_note || 'Questions adjust based on your recent performance patterns to ensure fair assessment.'}
                            </div>
                            {currentTierInfo.estimated_tier && (
                              <div className={`mt-2 pt-2 border-t ${theme('border-gray-600', 'border-gray-200')}`}>
                                <span className={theme('text-gray-400', 'text-gray-500')}>Your ability level: </span>
                                <span className="font-semibold" style={{ color: getTierColor(currentTierInfo.estimated_tier) }}>
                                  {getTierLabel(currentTierInfo.estimated_tier)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    <div
                      className="text-xl font-bold flex items-center gap-1 justify-end"
                      style={{
                        color: currentTierInfo.active_tier
                          ? getTierColor(currentTierInfo.active_tier)
                          : getCurrentThetaColor(displayTheta)
                      }}
                    >
                      {/* Display active_tier if available, otherwise fallback to theta-based tier */}
                      {currentTierInfo.active_tier
                        ? getTierLabel(currentTierInfo.active_tier)
                        : getThetaTierLabel(displayTheta)
                      }
                      {/* Show subtle indicator when tiers don't match */}
                      {!currentTierInfo.tier_aligned && currentTierInfo.estimated_tier && (
                        <span className={`text-xs ${theme('text-gray-400', 'text-gray-500')} font-normal`}>
                          ({getTierLabel(currentTierInfo.estimated_tier)})
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <div className={`text-xs font-semibold ${theme('text-gray-400', 'text-gray-700')} mb-2 uppercase tracking-wide`}>Proficiency (θ) Levels</div>
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

                {/* ✅ NEW: Precision Quality Card */}
                  {precisionQuality && (
                    <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mb-1`}>
                            Measurement Quality
                          </div>
                          <div
                            className="font-semibold text-sm"
                            style={{ color: precisionQuality.color }}
                          >
                            {precisionQuality.label}
                          </div>
                        </div>

                        {/* Star Rating */}
                        <div className="flex gap-0.5">
                          {[1, 2, 3, 4, 5].map(star => (
                            <svg
                              key={star}
                              className="w-4 h-4"
                              fill={star <= precisionQuality.stars ? precisionQuality.color : '#4B5563'}
                              viewBox="0 0 20 20"
                            >
                              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                          ))}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      {progressToTarget !== null && (
                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className={theme('text-gray-400', 'text-gray-500')}>
                              Progress to target
                            </span>
                            <span className={theme('text-gray-300', 'text-gray-600')}>
                              {Math.round(progressToTarget * 100)}%
                            </span>
                          </div>
                          <div className={`w-full h-1.5 ${theme('bg-gray-700', 'bg-gray-200')} rounded-full overflow-hidden`}>
                            <div
                              className="h-full transition-all duration-500 rounded-full"
                              style={{
                                width: `${Math.min(progressToTarget * 100, 100)}%`,
                                backgroundColor: precisionQuality.color
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )}

              <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-xl shadow-sm border p-4`}>
                <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-2 text-sm`}>Proficiency(θ) Progression</h3>
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
                          label={{ value: 'Proficiency(θ)', angle: -90, position: 'insideLeft', fontSize: 9, fill: chartColors.stroke }}
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
                          label={{ value: 'Proficiency(θ)', angle: -90, position: 'insideLeft', fontSize: 9, fill: chartColors.stroke }}
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