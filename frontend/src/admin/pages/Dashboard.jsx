import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { theme } from '../../config/theme';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalBanks: 0,
    totalItems: 0,
    totalTestTakers: 0,
    totalSessions: 0
  });
  const [recentSessions, setRecentSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const API_BASE = 'http://localhost:8000/api';

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch item banks
      const banksResponse = await fetch(`${API_BASE}/item-banks`);
      const banks = await banksResponse.json();

      // Fetch all sessions
      const sessionsResponse = await fetch(`${API_BASE}/sessions`);
      const sessions = await sessionsResponse.json();

      // Calculate unique test takers
      const uniqueUsers = new Set(sessions.map(s => s.username)).size;

      setStats({
        totalBanks: banks.length,
        totalItems: banks.reduce((sum, b) => sum + b.total_items, 0),
        totalTestTakers: uniqueUsers,
        totalSessions: sessions.length
      });

      // Get recent sessions (last 5)
      setRecentSessions(sessions.slice(0, 5));

      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return `${diffDays} days ago`;
  };

  const getActivityType = (session) => {
    return session.status === 'Completed' ? 'session' : 'active';
  };

  const getActivityMessage = (session) => {
    if (session.status === 'Completed') {
      return `${session.username} completed ${session.item_bank} assessment (θ=${session.theta.toFixed(2)})`;
    }
    return `${session.username} started ${session.item_bank} assessment`;
  };

  return (
    <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
      <div className="mb-8">
        <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Dashboard</h1>
        <p className={theme('text-gray-400', 'text-gray-600')}>Overview of your adaptive testing system</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} p-6 rounded-lg shadow hover:shadow-lg transition ${theme('border', '')}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`${theme('text-gray-400', 'text-gray-600')} text-sm font-medium mb-1`}>Item Banks</p>
              <p className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{stats.totalBanks}</p>
              <p className="text-sm text-green-600 mt-1">→ Active</p>
            </div>
            <div className={`${theme('bg-blue-900/50', 'bg-blue-100')} p-4 rounded-lg`}>
              <svg className={`w-8 h-8 ${theme('text-blue-400', 'text-blue-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} p-6 rounded-lg shadow hover:shadow-lg transition ${theme('border', '')}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`${theme('text-gray-400', 'text-gray-600')} text-sm font-medium mb-1`}>Total Questions</p>
              <p className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{stats.totalItems}</p>
              <p className="text-sm text-blue-600 mt-1">Across all banks</p>
            </div>
            <div className={`${theme('bg-green-900/50', 'bg-green-100')} p-4 rounded-lg`}>
              <svg className={`w-8 h-8 ${theme('text-green-400', 'text-green-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} p-6 rounded-lg shadow hover:shadow-lg transition ${theme('border', '')}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`${theme('text-gray-400', 'text-gray-600')} text-sm font-medium mb-1`}>Test Takers</p>
              <p className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{stats.totalTestTakers}</p>
              <p className="text-sm text-purple-600 mt-1">Total unique</p>
            </div>
            <div className={`${theme('bg-purple-900/50', 'bg-purple-100')} p-4 rounded-lg`}>
              <svg className={`w-8 h-8 ${theme('text-purple-400', 'text-purple-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} p-6 rounded-lg shadow hover:shadow-lg transition ${theme('border', '')}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`${theme('text-gray-400', 'text-gray-600')} text-sm font-medium mb-1`}>Sessions</p>
              <p className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{stats.totalSessions}</p>
              <p className="text-sm text-orange-600 mt-1">Total completed</p>
            </div>
            <div className={`${theme('bg-orange-900/50', 'bg-orange-100')} p-4 rounded-lg`}>
              <svg className={`w-8 h-8 ${theme('text-orange-400', 'text-orange-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className={`lg:col-span-2 ${theme('bg-gray-800 border-gray-700', 'bg-white')} rounded-lg shadow p-6 ${theme('border', '')}`}>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>Quick Actions</h2>
          <div className="grid grid-cols-3 gap-4">
            <Link
              to="/admin/upload"
              className={`p-6 border-2 border-dashed ${theme('border-gray-600 hover:border-blue-500 hover:bg-blue-900/20', 'border-gray-300 hover:border-blue-500 hover:bg-blue-50')} rounded-lg transition text-center group`}
            >
              <div className="text-4xl mb-2 group-hover:scale-110 transition">📤</div>
              <div className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>Upload Questions</div>
              <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mt-1`}>Add new item bank</div>
            </Link>

            <Link
              to="/admin/item-banks"
              className={`p-6 border-2 border-dashed ${theme('border-gray-600 hover:border-green-500 hover:bg-green-900/20', 'border-gray-300 hover:border-green-500 hover:bg-green-50')} rounded-lg transition text-center group`}
            >
              <div className="text-4xl mb-2 group-hover:scale-110 transition">⚙️</div>
              <div className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>Calibrate</div>
              <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mt-1`}>Run IRT calibration</div>
            </Link>

            <Link
              to="/admin/sessions"
              className={`p-6 border-2 border-dashed ${theme('border-gray-600 hover:border-purple-500 hover:bg-purple-900/20', 'border-gray-300 hover:border-purple-500 hover:bg-purple-50')} rounded-lg transition text-center group`}
            >
              <div className="text-4xl mb-2 group-hover:scale-110 transition">📊</div>
              <div className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>View Sessions</div>
              <div className={`text-sm ${theme('text-gray-400', 'text-gray-600')} mt-1`}>Test analytics</div>
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} rounded-lg shadow p-6 ${theme('border', '')}`}>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>Recent Activity</h2>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
            </div>
          ) : recentSessions.length === 0 ? (
            <div className={`text-center py-8 ${theme('text-gray-400', 'text-gray-500')}`}>
              No activity yet
            </div>
          ) : (
            <div className="space-y-4">
              {recentSessions.map((session) => {
                const activityType = getActivityType(session);
                return (
                  <div key={session.session_id} className={`flex items-start gap-3 pb-4 border-b ${theme('border-gray-700', 'border-gray-100')} last:border-0`}>
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      activityType === 'session' 
                        ? theme('bg-green-900/50', 'bg-green-100')
                        : theme('bg-blue-900/50', 'bg-blue-100')
                    }`}>
                      <span className="text-lg">
                        {activityType === 'session' ? '📊' : '⚡'}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${theme('text-gray-200', 'text-gray-900')}`}>
                        {getActivityMessage(session)}
                      </p>
                      <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>
                        {formatDate(session.started_at)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className={`mt-6 ${theme('bg-green-900/30 border-green-700', 'bg-green-50 border-green-200')} border rounded-lg p-4`}>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <div>
            <span className={`font-medium ${theme('text-green-300', 'text-green-900')}`}>System Status: </span>
            <span className={theme('text-green-400', 'text-green-700')}>All services operational</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;