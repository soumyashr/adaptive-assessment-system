// src/admin/pages/TestSessions.jsx - PROFESSIONAL DESIGN
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getThemeColors, DARK_MODE } from '../../config/theme';
import { Activity, Download, XCircle, Eye, TrendingUp, Users, FileText } from 'lucide-react';
import config from '../../config/config';
import notificationService from '../../services/notificationService';

const TestSessions = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [terminatingSession, setTerminatingSession] = useState(null);

  const API_BASE = config.API_BASE_URL;
  const colors = getThemeColors();

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleTerminateSession = async (sessionId, itemBank) => {
    if (!window.confirm(`Terminate session #${sessionId}?`)) return;

    setTerminatingSession(sessionId);
    try {
      const response = await fetch(
        `${API_BASE}/sessions/${sessionId}/terminate?item_bank_name=${itemBank}`,
        { method: 'POST' }
      );

      if (response.ok) {
        notificationService.success('Session terminated successfully');
        fetchSessions();
      } else {
        notificationService.error('Failed to terminate session');
      }
    } catch (error) {
      console.error('Error terminating session:', error);
      notificationService.error('Error terminating session');
    } finally {
      setTerminatingSession(null);
    }
  };

  const handleExportSession = async (sessionId, itemBank, username) => {
    try {
      const response = await fetch(
        `${API_BASE}/sessions/${sessionId}/export-pdf?item_bank_name=${itemBank}`
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `session_${sessionId}_${username}_report.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        notificationService.error('Failed to export session');
      }
    } catch (error) {
      console.error('Error exporting session:', error);
      notificationService.error('Error exporting session');
    }
  };

  const handleTerminateAllActive = async () => {
    const activeSessions = sessions.filter(s => s.status === 'Active');
    if (activeSessions.length === 0) {
      notificationService.success('No active sessions to terminate');
      return;
    }

    if (!window.confirm(`Terminate all ${activeSessions.length} active sessions?`)) return;

    try {
      const response = await fetch(`${API_BASE}/sessions/terminate-all`, {
        method: 'POST'
      });

      if (response.ok) {
        const result = await response.json();
        notificationService.success(`Terminated ${result.terminated_count} sessions successfully`);
        fetchSessions();
      } else {
        notificationService.error('Failed to terminate sessions');
      }
    } catch (error) {
      console.error('Error terminating all sessions:', error);
      notificationService.error('Error terminating sessions');
    }
  };

  const filteredSessions = sessions.filter(session => {
    if (filter === 'completed') return session.status === 'Completed';
    if (filter === 'active') return session.status === 'Active';
    return true;
  });

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getThetaColor = (theta) => {
    if (theta < -0.5) return '#EF4444';
    if (theta < 0.5) return '#F59E0B';
    if (theta < 1.5) return '#10B981';
    return '#3B82F6';
  };

  const completedCount = sessions.filter(s => s.status === 'Completed').length;
  const activeCount = sessions.filter(s => s.status === 'Active').length;

  const avgTheta = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + s.theta, 0) / sessions.length).toFixed(2)
    : '0.00';

  const avgAccuracy = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + s.accuracy, 0) / sessions.length * 100).toFixed(0)
    : '0';

  const HeaderStatCard = ({ icon: Icon, label, value, color }) => (
    <div style={{
      background: colors.cardBg,
      border: `1px solid ${colors.cardBorder}`,
      borderRadius: '10px',
      padding: '16px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '10px',
        background: color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon size={24} color="white" />
      </div>
      <div>
        <div style={{ fontSize: '12px', color: colors.textMuted, marginBottom: '2px' }}>
          {label}
        </div>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: colors.textPrimary }}>
          {value}
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ padding: '32px' }}>
      {/* Header */}
      <div
        style={{
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '10px',
          padding: '20px',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
        }}
      >
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '6px' }}>
            Assessment Sessions
          </h1>
          <p style={{ color: colors.textMuted, fontSize: '13px' }}>
            View and manage assessment sessions across all item banks
          </p>
        </div>

        {activeCount > 0 && (
          <button
            onClick={handleTerminateAllActive}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: DARK_MODE ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid #FEE2E2',
              background: DARK_MODE ? 'rgba(30, 30, 30, 1)' : '#FEF2F2',
              color: DARK_MODE ? '#FCA5A5' : '#DC2626',
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = DARK_MODE ? 'rgba(40, 25, 25, 1)' : '#FEE2E2';
              e.currentTarget.style.borderColor = DARK_MODE ? 'rgba(239, 68, 68, 0.4)' : '#FCA5A5';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = DARK_MODE ? 'rgba(30, 30, 30, 1)' : '#FEF2F2';
              e.currentTarget.style.borderColor = DARK_MODE ? 'rgba(239, 68, 68, 0.2)' : '#FEE2E2';
            }}
          >
            <XCircle size={18} />
            Terminate All ({activeCount})
          </button>
        )}
      </div>

      {/* Stats Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <HeaderStatCard icon={Activity} label="Total Sessions" value={sessions.length} color="#3B82F6" />
        <HeaderStatCard icon={Users} label="Completed" value={completedCount} color="#10B981" />
        <HeaderStatCard icon={TrendingUp} label="Avg Theta" value={avgTheta} color="#8B5CF6" />
        <HeaderStatCard icon={FileText} label="Avg Accuracy" value={`${avgAccuracy}%`} color="#F59E0B" />
      </div>

      {/* Filter Tabs */}
      <div style={{
        background: colors.cardBg,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: '10px',
        marginBottom: '16px',
        overflow: 'hidden'
      }}>
        <div style={{ borderBottom: `1px solid ${colors.cardBorder}`,
            display: 'flex' }}>
          {[
            { id: 'all', label: `All Sessions (${sessions.length})` },
            { id: 'completed', label: `Completed (${completedCount})` },
            { id: 'active', label: `Active (${activeCount})` }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              style={{
                flex: 1,
                padding: '12px 16px',
                border: 'none',
                background: 'transparent',
                borderBottom: `2px solid ${filter === tab.id ? colors.primary : 'transparent'}`,
                color: filter === tab.id ? colors.primary : colors.textMuted,
                fontWeight: filter === tab.id ? '600' : '500',
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Sessions Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: colors.cardBg }}>
            <thead>
              <tr style={{
                  background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'

              }}>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>ID</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>User</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Item Bank</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Status</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Theta</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Questions</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Accuracy</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Started</th>
                <th style={{padding: '12px 16px', textAlign: 'left', fontSize: '11px',fontWeight: '600',color: colors.textMuted, textTransform: 'uppercase', background: DARK_MODE ? '#0f0f0f' : '#F9FAFB'}}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr style={{ background: colors.cardBg }}>
                  <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: colors.textMuted }}>
                    Loading sessions...
                  </td>
                </tr>
              ) : filteredSessions.length === 0 ? (
                <tr style={{ background: colors.cardBg }}>
                  <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: colors.textMuted }}>
                    No {filter !== 'all' ? filter : ''} sessions found
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => (
                  <tr
                    key={`${session.item_bank}-${session.session_id}`}
                    style={{
                      borderBottom: `1px solid ${colors.cardBorder}`,
                      transition: 'background 0.2s',
                      background: colors.cardBg
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = DARK_MODE ? 'rgba(255,255,255,0.03)' : '#F9FAFB';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = colors.cardBg;
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '13px', fontWeight: '600', color: colors.textPrimary }}>
                      #{session.session_id}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: colors.textPrimary }}>
                      {session.username}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: colors.textMuted }}>
                      {session.item_bank}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: '600',
                        background: session.status === 'Completed' ? (DARK_MODE ? 'rgba(16, 185, 129, 0.2)' : '#D1FAE5') : (DARK_MODE ? 'rgba(251, 191, 36, 0.2)' : '#FEF3C7'),
                        color: session.status === 'Completed' ? '#10B981' : '#F59E0B'
                      }}>
                        {session.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600',
                        background: `${getThetaColor(session.theta)}15`,
                        color: getThetaColor(session.theta),
                        fontFamily: 'monospace'
                      }}>
                        {session.theta.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: colors.textMuted }}>
                      {session.questions_asked}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: colors.textMuted }}>
                      {(session.accuracy * 100).toFixed(0)}%
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '12px', color: colors.textMuted }}>
                      {formatDate(session.started_at)}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        {/* View Button - Primary */}
                        <button
                          onClick={() => navigate(`/admin/sessions/${session.session_id}`)}
                          style={{
                            padding: '6px 10px',
                            borderRadius: '6px',
                            border: `1px solid ${colors.cardBorder}`,
                            background: colors.cardBg,
                            color: colors.textPrimary,
                            fontSize: '12px',
                            fontWeight: '500',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = colors.primary;
                            e.currentTarget.style.color = 'white';
                            e.currentTarget.style.borderColor = colors.primary;
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = colors.cardBg;
                            e.currentTarget.style.color = colors.textPrimary;
                            e.currentTarget.style.borderColor = colors.cardBorder;
                          }}
                          title="View Details"
                        >
                          <Eye size={14} />
                          View
                        </button>

                        {/* Export Button - Neutral */}
                        <button
                          onClick={() => handleExportSession(session.session_id, session.item_bank, session.username)}
                          style={{
                            padding: '6px 10px',
                            borderRadius: '6px',
                            border: `1px solid ${colors.cardBorder}`,
                            background: colors.cardBg,
                            color: colors.textPrimary,
                            fontSize: '12px',
                            fontWeight: '500',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = DARK_MODE ? '#2a2a2a' : '#F3F4F6';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = colors.cardBg;
                          }}
                          title="Export PDF"
                        >
                          <Download size={14} />
                          Export
                        </button>

                        {/* Terminate Button (only for Active sessions) - Subtle */}
                        {session.status === 'Active' && (
                          <button
                            onClick={() => handleTerminateSession(session.session_id, session.item_bank)}
                            disabled={terminatingSession === session.session_id}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              border: `1px solid ${colors.cardBorder}`,
                              background: colors.cardBg,
                              color: colors.textMuted,
                              fontSize: '12px',
                              fontWeight: '500',
                              cursor: terminatingSession === session.session_id ? 'not-allowed' : 'pointer',
                              opacity: terminatingSession === session.session_id ? 0.5 : 1,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                              if (terminatingSession !== session.session_id) {
                                e.currentTarget.style.background = '#FEE2E2';
                                e.currentTarget.style.color = '#EF4444';
                                e.currentTarget.style.borderColor = '#EF4444';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (terminatingSession !== session.session_id) {
                                e.currentTarget.style.background = colors.cardBg;
                                e.currentTarget.style.color = colors.textMuted;
                                e.currentTarget.style.borderColor = colors.cardBorder;
                              }
                            }}
                            title="Terminate Session"
                          >
                            <XCircle size={14} />
                            {terminatingSession === session.session_id ? '...' : 'End'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TestSessions;