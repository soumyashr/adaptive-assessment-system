import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, ScatterChart,
  Scatter, Cell, Tooltip, ComposedChart, ReferenceLine, Legend,
  BarChart, Bar
} from 'recharts';

// Import theme from config
import { DARK_MODE } from '../../config/theme';
import config from '../../config/config';


const SessionDetail = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sessionData, setSessionData] = useState(null);
  const [comparativeData, setComparativeData] = useState(null);


  const API_BASE = config.API_BASE_URL;


  // Theme helper function
  const theme = (darkValue, lightValue) => DARK_MODE ? darkValue : lightValue;

  // Export PDF function
  const handleExportPDF = async () => {
    try {
      const response = await fetch(
        `${API_BASE}/sessions/${sessionId}/export-pdf?item_bank_name=${sessionData.item_bank}`
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `assessment_report_${sessionData.item_bank}_${sessionId}_${sessionData.username}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Failed to export session report');
        console.error('Export failed with status:', response.status);
      }
    } catch (error) {
      console.error('Error exporting session:', error);
      alert('Error exporting session report');
    }
  };

  // Professional color palette
  const colors = {
    primary: theme('#2563EB', '#3B82F6'),      // Blue
    success: theme('#059669', '#10B981'),      // Green
    warning: theme('#D97706', '#F59E0B'),      // Amber
    danger: theme('#DC2626', '#EF4444'),       // Red
    purple: theme('#7C3AED', '#8B5CF6'),       // Purple
    user: '#F59E0B',                           // Amber for user bars
    userBorder: '#000000'                      // Black border
  };

  // Custom Tooltip for Histogram
  const HistogramTooltip = ({ active, payload, label, metricName }) => {
    if (active && payload && payload.length) {
      return (
        <div
          style={{
            backgroundColor: theme('#1F2937', '#FFFFFF'),
            border: `1px solid ${theme('#374151', '#E5E7EB')}`,
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '13px',
            color: theme('#FFFFFF', '#000000')
          }}
        >
          <div style={{ marginBottom: '6px', fontWeight: 'bold' }}>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>{metricName}: </span>
            <span style={{ color: colors.primary }}>{label}</span>
          </div>
          <div>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>Users: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{payload[0].value}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for ICC Curve
  const ICCTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: theme('#1F2937', '#FFFFFF'),
            border: `1px solid ${theme('#374151', '#E5E7EB')}`,
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '13px',
            color: theme('#FFFFFF', '#000000')
          }}
        >
          <div style={{ marginBottom: '6px' }}>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>θ: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.x.toFixed(2)}</span>
          </div>
          <div>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>P(correct): </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.p.toFixed(3)}</span>
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
            backgroundColor: theme('#1F2937', '#FFFFFF'),
            border: `1px solid ${theme('#374151', '#E5E7EB')}`,
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '13px',
            color: theme('#FFFFFF', '#000000')
          }}
        >
          <div style={{ marginBottom: '6px' }}>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>Question #: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.question}</span>
          </div>
          <div>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>θ: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.theta.toFixed(2)}</span>
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
            backgroundColor: theme('#1F2937', '#FFFFFF'),
            border: `1px solid ${theme('#374151', '#E5E7EB')}`,
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '13px',
            color: theme('#FFFFFF', '#000000')
          }}
        >
          <div style={{ marginBottom: '6px' }}>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>Question #: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.question}</span>
          </div>
          <div style={{ marginBottom: '6px' }}>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>Difficulty: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.x.toFixed(2)}</span>
          </div>
          <div>
            <span style={{ color: theme('#9CA3AF', '#6B7280') }}>θ: </span>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>{data.y.toFixed(2)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for Radar Chart
  const RadarTooltip = ({ active, payload }) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: theme('#1F2937', '#FFFFFF'),
            border: '1px solid ' + theme('#374151', '#E5E7EB'),
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '13px',
            color: theme('#FFFFFF', '#000000')
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: '8px', color: theme('#F3F4F6', '#374151') }}>
            {data.topic}
          </div>
          <div style={{ marginBottom: '6px' }}>
            <span style={{ color: colors.success, fontWeight: 'bold' }}>Your Accuracy: </span>
            <span style={{ color: theme('#FFFFFF', '#000000'), fontWeight: 'bold' }}>
              {data['Your Accuracy'].toFixed(1)}%
            </span>
          </div>
          <div>
            <span style={{ color: colors.primary, fontWeight: 'bold' }}>Your θ: </span>
            <span style={{ color: theme('#FFFFFF', '#000000'), fontWeight: 'bold' }}>
              {((data['Your Proficiency'] / 100) * 6 - 3).toFixed(2)}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  const loadSessionData = async () => {
    try {
      const sessionsRes = await fetch(`${API_BASE}/sessions`);
      const sessions = await sessionsRes.json();

      const currentSession = sessions.find(s => s.session_id === parseInt(sessionId));

      if (!currentSession) {
        console.error('Session not found');
        setLoading(false);
        return;
      }

      const resultsRes = await fetch(
        `${API_BASE}/assessments/${sessionId}/results?item_bank_name=${currentSession.item_bank}`
      );
      const results = await resultsRes.json();

      const sameItemBankSessions = sessions.filter(
        s => s.item_bank === currentSession.item_bank && s.status === 'Completed'
      );

      setSessionData({ ...currentSession, ...results });
      calculateComparativeMetrics(results, sameItemBankSessions);

      setLoading(false);
    } catch (error) {
      console.error('Error loading session data:', error);
      setLoading(false);
    }
  };

  const calculateComparativeMetrics = (currentResults, allSessions) => {
    const thetas = allSessions.map(s => s.theta).sort((a, b) => a - b);
    const accuracies = allSessions.map(s => s.accuracy * 100).sort((a, b) => a - b);
    const questionCounts = allSessions.map(s => s.questions_asked).sort((a, b) => a - b);

    const calculatePercentile = (value, sortedArray) => {
      const index = sortedArray.findIndex(v => v >= value);
      if (index === -1) return 100;
      return Math.round((index / sortedArray.length) * 100);
    };

    const average = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;

    const createHistogram = (data, userValue, binCount = 10) => {
      const min = Math.min(...data);
      const max = Math.max(...data);
      const binSize = (max - min) / binCount;

      const bins = Array(binCount).fill(0).map((_, i) => ({
        bin: parseFloat((min + (i * binSize)).toFixed(2)),
        count: 0,
        isUser: false
      }));

      data.forEach(value => {
        const binIndex = Math.min(Math.floor((value - min) / binSize), binCount - 1);
        bins[binIndex].count++;
      });

      const userBinIndex = Math.min(Math.floor((userValue - min) / binSize), binCount - 1);
      if (userBinIndex >= 0 && userBinIndex < bins.length) {
        bins[userBinIndex].isUser = true;
      }

      return bins;
    };

    setComparativeData({
      thetaPercentile: calculatePercentile(currentResults.final_theta, thetas),
      accuracyPercentile: calculatePercentile(currentResults.accuracy * 100, accuracies),
      questionsPercentile: 100 - calculatePercentile(currentResults.questions_asked, questionCounts),
      avgTheta: average(thetas),
      avgAccuracy: average(accuracies) / 100,
      avgQuestions: average(questionCounts),
      totalUsers: allSessions.length,
      thetaHistogram: createHistogram(thetas, currentResults.final_theta),
      accuracyHistogram: createHistogram(accuracies, currentResults.accuracy * 100),
      questionsHistogram: createHistogram(questionCounts, currentResults.questions_asked)
    });
  };

  const generateICCData = (theta) => {
    const data = [];
    for (let x = -3; x <= 3; x += 0.1) {
      const p = 0.25 + (0.75) / (1 + Math.exp(-1.2 * (x - theta)));
      data.push({ x: parseFloat(x.toFixed(2)), p: parseFloat(p.toFixed(3)) });
    }
    return data;
  };

  const generateThetaProgression = (responses) => {
    return responses.map((resp, idx) => ({
      question: idx + 1,
      theta: parseFloat(resp.theta_after.toFixed(2)),
      correct: resp.is_correct
    }));
  };

  const generateResponsePattern = (responses) => {
    return responses.map((resp, idx) => ({
      x: parseFloat((resp.difficulty || 0).toFixed(2)),
      y: parseFloat(resp.theta_after.toFixed(2)),
      correct: resp.is_correct,
      question: idx + 1
    }));
  };

  // Generate topic recommendations
  const getTopicRecommendations = () => {
    if (!sessionData.topic_performance) return null;

    const topics = Object.values(sessionData.topic_performance);

    // Sort by accuracy to identify weak topics
    const weakTopics = topics
      .filter(t => t.accuracy < 0.6)
      .sort((a, b) => a.accuracy - b.accuracy)
      .slice(0, 3);

    // Identify topics for practice
    const practiceTopics = topics
      .filter(t => t.accuracy >= 0.6 && t.accuracy < 0.8)
      .sort((a, b) => a.accuracy - b.accuracy)
      .slice(0, 2);

    return {
      weak: weakTopics,
      practice: practiceTopics
    };
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-screen ${theme('bg-gray-900', 'bg-gray-50')}`}>
        <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${theme('border-blue-500', 'border-indigo-600')}`}></div>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
        <button
          onClick={() => navigate('/admin/sessions')}
          className={`${theme('text-blue-400 hover:text-blue-300', 'text-blue-600 hover:text-blue-700')} mb-4 flex items-center`}
        >
          ← Back to Sessions
        </button>
        <div className={theme('text-white', 'text-gray-900')}>Session not found</div>
      </div>
    );
  }

  const iccData = generateICCData(sessionData.final_theta);
  const thetaProgression = generateThetaProgression(sessionData.responses);
  const responsePattern = generateResponsePattern(sessionData.responses);
  const recommendations = getTopicRecommendations();

  return (
    <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/admin/sessions')}
          className={`${theme('text-blue-400 hover:text-blue-300', 'text-blue-600 hover:text-blue-700')} mb-4 flex items-center`}
        >
          ← Back to Sessions
        </button>
        <div className="flex justify-between items-start">
          <div>
            <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>
              Session #{sessionData.session_id}
            </h1>
            <div className={theme('text-gray-400', 'text-gray-600')}>
              User: <span className={`${theme('text-white', 'text-gray-900')} font-medium`}>{sessionData.username}</span>
              {' '} • Item Bank: <span className={`${theme('text-white', 'text-gray-900')} font-medium`}>{sessionData.item_bank}</span>
            </div>
          </div>
          <button
            onClick={handleExportPDF}
            className={`px-4 py-2 ${theme('bg-blue-600 hover:bg-blue-700', 'bg-indigo-600 hover:bg-indigo-700')} text-white rounded-lg flex items-center gap-2`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 10h6m-6 4h10" />
            </svg>
            Export PDF
          </button>
        </div>
      </div>

      {/* Performance Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-4`}>
          <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-1`}>Final θ</div>
          <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-1`}>
            {sessionData.final_theta?.toFixed(2)}
          </div>
          {comparativeData && (
            <div className="text-xs" style={{ color: colors.primary }}>
              {comparativeData.thetaPercentile}th percentile
            </div>
          )}
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-4`}>
          <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-1`}>Accuracy</div>
          <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-1`}>
            {(sessionData.accuracy * 100).toFixed(0)}%
          </div>
          {comparativeData && (
            <div className="text-xs" style={{ color: colors.success }}>
              {comparativeData.accuracyPercentile}th percentile
            </div>
          )}
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-4`}>
          <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-1`}>Questions</div>
          <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')} mb-1`}>
            {sessionData.questions_asked}
          </div>
          {comparativeData && (
            <div className={`text-xs ${theme('text-gray-400', 'text-gray-600')}`}>
              Avg: {comparativeData.avgQuestions.toFixed(0)}
            </div>
          )}
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-4`}>
          <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-1`}>Tier</div>
          <div className={`text-2xl font-bold ${theme('text-white', 'text-gray-900')}`}>
            {sessionData.tier}
          </div>
          {comparativeData && (
            <div className={`text-xs ${theme('text-gray-400', 'text-gray-600')}`}>
              vs {comparativeData.totalUsers} users
            </div>
          )}
        </div>
      </div>

      {/* Spider Chart - UPDATED WITH IMPROVED STYLING */}
      {sessionData.topic_performance && (
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-6 mb-6`}>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>
            Topic Performance Overview
          </h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={Object.values(sessionData.topic_performance).map(topic => ({
                topic: topic.topic.charAt(0).toUpperCase() + topic.topic.slice(1),
                'Your Accuracy': topic.accuracy * 100,
                'Your Proficiency': ((topic.theta + 3) / 6) * 100,
              }))}>
                <PolarGrid
                  stroke={theme('#4B5563', '#D1D5DB')}
                  strokeWidth={1.5}
                  strokeDasharray="3 3"
                />
                <PolarAngleAxis
                  dataKey="topic"
                  tick={{ fill: theme('#F3F4F6', '#374151'), fontSize: 13, fontWeight: 600 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fill: theme('#D1D5DB', '#6B7280'), fontSize: 11 }}
                  stroke={theme('#4B5563', '#D1D5DB')}
                />
                <Radar
                  name="Your Accuracy %"
                  dataKey="Your Accuracy"
                  stroke={colors.success}
                  fill={colors.success}
                  fillOpacity={0.25}
                  strokeWidth={2.5}
                />
                <Radar
                  name="Your Proficiency θ"
                  dataKey="Your Proficiency"
                  stroke={colors.primary}
                  fill={colors.primary}
                  fillOpacity={0.15}
                  strokeWidth={2.5}
                />
                <Legend
                  wrapperStyle={{
                    fontSize: '13px',
                    color: theme('#F3F4F6', '#374151'),
                    fontWeight: 600,
                    paddingTop: '20px'
                  }}
                />
                <Tooltip content={<RadarTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Performance Distribution - UPDATED WITH USER BAR STYLING */}
      {comparativeData && (
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-6 mb-6`}>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>
            Performance Distribution
          </h2>
          <div className="grid grid-cols-3 gap-6">
            {/* θ Distribution */}
            <div>
              <div className="text-center mb-4">
                <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-2`}>θ Distribution</div>
                <div className="text-4xl font-bold mb-1" style={{ color: colors.primary }}>
                  {comparativeData.thetaPercentile}%
                </div>
                <div className={`text-xs ${theme('text-gray-500', 'text-gray-600')}`}>
                  Your θ: {sessionData.final_theta.toFixed(2)} vs Avg: {comparativeData.avgTheta.toFixed(2)}
                </div>
              </div>
              <div className={`h-32 ${theme('bg-gray-900', 'bg-gray-100')} rounded-lg p-2`}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparativeData.thetaHistogram || []}>
                    <XAxis
                      dataKey="bin"
                      fontSize={8}
                      stroke={theme('#9CA3AF', '#6B7280')}
                      tickFormatter={(value) => value.toFixed(2)}
                    />
                    <YAxis fontSize={8} stroke={theme('#9CA3AF', '#6B7280')} />
                    <Tooltip
                      content={<HistogramTooltip metricName="θ Range" />}
                      cursor={{ fill: theme('rgba(37, 99, 235, 0.1)', 'rgba(59, 130, 246, 0.1)') }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {(comparativeData.thetaHistogram || []).map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isUser ? colors.user : colors.primary}
                          stroke={entry.isUser ? colors.userBorder : 'transparent'}
                          strokeWidth={entry.isUser ? 3 : 0}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 text-center text-xs">
                <span className="inline-flex items-center" style={{ color: colors.user }}>
                  <span className="w-3 h-3 rounded mr-1.5 border-2" style={{ backgroundColor: colors.user, borderColor: colors.userBorder }}></span>
                  Your Performance
                </span>
              </div>
            </div>

            {/* Accuracy Distribution */}
            <div>
              <div className="text-center mb-4">
                <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-2`}>Accuracy Percentile</div>
                <div className="text-4xl font-bold mb-1" style={{ color: colors.success }}>
                  {comparativeData.accuracyPercentile}%
                </div>
                <div className={`text-xs ${theme('text-gray-500', 'text-gray-600')}`}>
                  Your: {(sessionData.accuracy * 100).toFixed(0)}% vs Avg: {(comparativeData.avgAccuracy * 100).toFixed(0)}%
                </div>
              </div>
              <div className={`h-32 ${theme('bg-gray-900', 'bg-gray-100')} rounded-lg p-2`}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparativeData.accuracyHistogram || []}>
                    <XAxis
                      dataKey="bin"
                      fontSize={8}
                      stroke={theme('#9CA3AF', '#6B7280')}
                      tickFormatter={(value) => `${value.toFixed(0)}%`}
                    />
                    <YAxis fontSize={8} stroke={theme('#9CA3AF', '#6B7280')} />
                    <Tooltip
                      content={<HistogramTooltip metricName="Accuracy Range" />}
                      cursor={{ fill: theme('rgba(5, 150, 105, 0.1)', 'rgba(16, 185, 129, 0.1)') }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {(comparativeData.accuracyHistogram || []).map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isUser ? colors.user : colors.success}
                          stroke={entry.isUser ? colors.userBorder : 'transparent'}
                          strokeWidth={entry.isUser ? 3 : 0}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 text-center text-xs">
                <span className="inline-flex items-center" style={{ color: colors.user }}>
                  <span className="w-3 h-3 rounded mr-1.5 border-2" style={{ backgroundColor: colors.user, borderColor: colors.userBorder }}></span>
                  Your Performance
                </span>
              </div>
            </div>

            {/* Efficiency Distribution */}
            <div>
              <div className="text-center mb-4">
                <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mb-2`}>Efficiency Percentile</div>
                <div className="text-4xl font-bold mb-1" style={{ color: colors.purple }}>
                  {comparativeData.questionsPercentile}%
                </div>
                <div className={`text-xs ${theme('text-gray-500', 'text-gray-600')}`}>
                  Questions: {sessionData.questions_asked} vs Avg: {comparativeData.avgQuestions.toFixed(0)}
                </div>
                <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>
                  (Fewer questions = Higher efficiency)
                </div>
              </div>
              <div className={`h-32 ${theme('bg-gray-900', 'bg-gray-100')} rounded-lg p-2`}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparativeData.questionsHistogram || []}>
                    <XAxis
                      dataKey="bin"
                      fontSize={8}
                      stroke={theme('#9CA3AF', '#6B7280')}
                      tickFormatter={(value) => value.toFixed(0)}
                    />
                    <YAxis fontSize={8} stroke={theme('#9CA3AF', '#6B7280')} />
                    <Tooltip
                      content={<HistogramTooltip metricName="Question Count" />}
                      cursor={{ fill: theme('rgba(124, 58, 237, 0.1)', 'rgba(139, 92, 246, 0.1)') }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {(comparativeData.questionsHistogram || []).map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isUser ? colors.user : colors.purple}
                          stroke={entry.isUser ? colors.userBorder : 'transparent'}
                          strokeWidth={entry.isUser ? 3 : 0}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 text-center text-xs">
                <span className="inline-flex items-center" style={{ color: colors.user }}>
                  <span className="w-3 h-3 rounded mr-1.5 border-2" style={{ backgroundColor: colors.user, borderColor: colors.userBorder }}></span>
                  Your Performance
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* IRT Analysis Charts */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        {/* ICC Chart */}
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-5`}>
          <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Item Characteristic Curve</h3>
          <p className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mb-3`}>Probability of correct response vs θ</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={iccData}>
                <XAxis
                  dataKey="x"
                  domain={[-3, 3]}
                  type="number"
                  fontSize={10}
                  stroke={theme('#9CA3AF', '#6B7280')}
                />
                <YAxis domain={[0, 1]} fontSize={10} stroke={theme('#9CA3AF', '#6B7280')} />
                <Tooltip content={<ICCTooltip />} />
                <ReferenceLine
                  x={sessionData.final_theta}
                  stroke={colors.primary}
                  strokeWidth={2}
                  strokeDasharray="3 3"
                />
                <Line
                  type="monotone"
                  dataKey="p"
                  stroke={colors.primary}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: '#FFFFFF', stroke: colors.primary, strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Theta Progression */}
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-5`}>
          <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>θ Progression</h3>
          <p className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mb-3`}>Proficiency estimate over time</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={thetaProgression}>
                <XAxis dataKey="question" fontSize={10} stroke={theme('#9CA3AF', '#6B7280')} />
                <YAxis domain={[-2, 2]} fontSize={10} stroke={theme('#9CA3AF', '#6B7280')} />
                <Tooltip content={<ThetaProgressionTooltip />} />
                <Line
                  type="monotone"
                  dataKey="theta"
                  stroke={colors.primary}
                  strokeWidth={2}
                  dot={false}
                />
                <Scatter dataKey="theta">
                  {thetaProgression.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.correct ? colors.success : colors.danger} />
                  ))}
                </Scatter>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex justify-center space-x-3 text-xs">
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full mr-1" style={{ backgroundColor: colors.success }}></div>
              <span className={theme('text-gray-300', 'text-gray-700')}>Correct</span>
            </div>
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full mr-1" style={{ backgroundColor: colors.danger }}></div>
              <span className={theme('text-gray-300', 'text-gray-700')}>Incorrect</span>
            </div>
          </div>
        </div>

        {/* Response Pattern */}
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-5`}>
          <h3 className={`font-semibold ${theme('text-white', 'text-gray-900')} mb-1 text-sm`}>Response Pattern</h3>
          <p className={`text-xs ${theme('text-gray-400', 'text-gray-600')} mb-3`}>Difficulty vs Proficiency</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <XAxis dataKey="x" type="number" fontSize={10} stroke={theme('#9CA3AF', '#6B7280')} />
                <YAxis domain={[-2, 2]} fontSize={10} stroke={theme('#9CA3AF', '#6B7280')} />
                <Tooltip content={<ResponsePatternTooltip />} />
                <Scatter data={responsePattern} dataKey="y">
                  {responsePattern.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.correct ? colors.success : colors.danger}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex justify-center space-x-3 text-xs">
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full mr-1" style={{ backgroundColor: colors.success }}></div>
              <span className={theme('text-gray-300', 'text-gray-700')}>Correct</span>
            </div>
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full mr-1" style={{ backgroundColor: colors.danger }}></div>
              <span className={theme('text-gray-300', 'text-gray-700')}>Incorrect</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recommended Topics Section */}
      {recommendations && (recommendations.weak.length > 0 || recommendations.practice.length > 0) && (
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-xl p-6`}>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>
            Recommended Topics for Further Study
          </h2>

          {/* Priority Topics */}
          {recommendations.weak.length > 0 && (
            <div className="mb-6">
              <h3 className={`text-lg font-semibold ${theme('text-red-400', 'text-red-600')} mb-3 flex items-center`}>
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Priority Focus Areas
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {recommendations.weak.map((topic, idx) => (
                  <div key={idx} className={`${theme('bg-red-900/20 border-red-700', 'bg-red-50 border-red-200')} border rounded-lg p-4`}>
                    <div className="flex justify-between items-start mb-2">
                      <h4 className={`font-semibold ${theme('text-red-300', 'text-red-900')} capitalize`}>
                        {topic.topic}
                      </h4>
                      <span
                        className={`px-2 py-1 ${theme('bg-red-800', 'bg-red-200')} ${theme('text-red-200', 'text-red-800')} rounded text-xs font-bold cursor-help`}
                        title={'Accuracy: ' + (isNaN(topic.accuracy) ? '0' : (topic.accuracy * 100).toFixed(0)) + '% (' + (isNaN(topic.accuracy) ? '0' : Math.round(topic.accuracy * topic.questions_answered)) + '/' + (topic.questions_answered || 0) + ' correct)'}
                      >
                        {isNaN(topic.accuracy) ? '0' : (topic.accuracy * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className={`text-xs ${theme('text-red-400', 'text-red-700')} mb-2`}>
                      {topic.questions_answered || 0} question{(topic.questions_answered !== 1) ? 's' : ''} • θ: {isNaN(topic.theta) ? '0.00' : topic.theta.toFixed(2)}
                    </p>
                    <p className={`text-sm ${theme('text-gray-400', 'text-gray-700')}`}>
                      Focus on foundational concepts and practice 5-10 questions daily
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Practice Topics */}
          {recommendations.practice.length > 0 && (
            <div>
              <h3 className={`text-lg font-semibold ${theme('text-yellow-400', 'text-yellow-600')} mb-3 flex items-center`}>
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                Continue Practicing
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recommendations.practice.map((topic, idx) => (
                  <div key={idx} className={`${theme('bg-yellow-900/20 border-yellow-700', 'bg-yellow-50 border-yellow-200')} border rounded-lg p-4`}>
                    <div className="flex justify-between items-start mb-2">
                      <h4 className={`font-semibold ${theme('text-yellow-300', 'text-yellow-900')} capitalize`}>
                        {topic.topic}
                      </h4>
                      <span
                        className={`px-2 py-1 ${theme('bg-yellow-800', 'bg-yellow-200')} ${theme('text-yellow-200', 'text-yellow-800')} rounded text-xs font-bold cursor-help`}
                        title={'Accuracy: ' + (topic.accuracy * 100).toFixed(0) + '% (' + Math.round(topic.accuracy * topic.questions_answered) + '/' + topic.questions_answered + ' correct)'}
                      >
                        {(topic.accuracy * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className={`text-xs ${theme('text-yellow-400', 'text-yellow-700')} mb-2`}>
                      {topic.questions_answered} question{topic.questions_answered !== 1 ? 's' : ''} • θ: {topic.theta.toFixed(2)}
                    </p>
                    <p className={`text-sm ${theme('text-gray-400', 'text-gray-700')}`}>
                      Good progress! Practice 3-5 problems daily to master this topic
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SessionDetail;