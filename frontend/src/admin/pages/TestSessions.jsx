import React, { useState, useEffect } from 'react';
import { theme } from '../../config/theme';
import { useNavigate } from 'react-router-dom';


const TestSessions = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, completed, active

  const API_BASE = 'http://localhost:8000/api';

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      } else {
        throw new Error('Failed to fetch sessions');
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessions([]); // Set empty array on error
    } finally {
      setLoading(false);
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
    if (theta < -0.5) return 'bg-red-100 text-red-800';
    if (theta < 0.5) return 'bg-yellow-100 text-yellow-800';
    if (theta < 1.5) return 'bg-green-100 text-green-800';
    return 'bg-blue-100 text-blue-800';
  };

  const completedCount = sessions.filter(s => s.status === 'Completed').length;
  const activeCount = sessions.filter(s => s.status === 'Active').length;

  // Calculate statistics
  const avgTheta = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + s.theta, 0) / sessions.length).toFixed(2)
    : '0.00';

  const avgAccuracy = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + s.accuracy, 0) / sessions.length * 100).toFixed(0)
    : '0';

  const avgQuestions = sessions.length > 0
    ? Math.round(sessions.reduce((sum, s) => sum + s.questions_asked, 0) / sessions.length)
    : 0;

  const completionRate = sessions.length > 0
    ? (completedCount / sessions.length * 100).toFixed(0)
    : '0';

  return (
    <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
      <div className="mb-8">
        <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Test Sessions</h1>
        <p className={theme('text-gray-400', 'text-gray-600')}>View and manage assessment sessions across all item banks</p>
      </div>

      {/* Filter Tabs */}
      <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} rounded-lg shadow mb-6 ${theme('border', '')}`}>
        <div className={`border-b ${theme('border-gray-700', 'border-gray-200')}`}>
          <nav className="flex -mb-px">
            <button
              onClick={() => setFilter('all')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition ${
                filter === 'all'
                  ? 'border-blue-500 text-blue-600'
                  : theme('border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600', 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300')
              }`}
            >
              All Sessions ({sessions.length})
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition ${
                filter === 'completed'
                  ? 'border-blue-500 text-blue-600'
                  : theme('border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600', 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300')
              }`}
            >
              Completed ({completedCount})
            </button>
            <button
              onClick={() => setFilter('active')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition ${
                filter === 'active'
                  ? 'border-blue-500 text-blue-600'
                  : theme('border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600', 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300')
              }`}
            >
              Active ({activeCount})
            </button>
          </nav>
        </div>
      </div>

      {/* Sessions Table */}
      <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} rounded-lg shadow overflow-hidden ${theme('border', '')}`}>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className={theme('bg-gray-700', 'bg-gray-50')}>
            <tr>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Session ID
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                User
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Item Bank
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Status
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Theta (θ)
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Questions
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Accuracy
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Started
              </th>
              <th className={`px-6 py-3 text-left text-xs font-medium ${theme('text-gray-300', 'text-gray-500')} uppercase tracking-wider`}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody className={`${theme('bg-gray-800', 'bg-white')} divide-y ${theme('divide-gray-700', 'divide-gray-200')}`}>
            {loading ? (
              <tr>
                <td colSpan="9" className={`px-6 py-12 text-center ${theme('text-gray-400', 'text-gray-500')}`}>
                  <div className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                    Loading sessions...
                  </div>
                </td>
              </tr>
            ) : filteredSessions.length === 0 ? (
              <tr>
                <td colSpan="9" className={`px-6 py-12 text-center ${theme('text-gray-400', 'text-gray-500')}`}>
                  No sessions found
                </td>
              </tr>
            ) : (
              filteredSessions.map((session) => (
                <tr key={session.session_id} className={theme('hover:bg-gray-700', 'hover:bg-gray-50')}>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${theme('text-gray-300', 'text-gray-900')}`}>
                    #{session.session_id}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${theme('text-gray-200', 'text-gray-900')}`}>
                    {session.username}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${theme('text-gray-300', 'text-gray-600')}`}>
                    {session.item_bank}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      session.status === 'Completed'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {session.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getThetaColor(session.theta)}`}>
                      θ = {session.theta.toFixed(2)}
                    </span>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${theme('text-gray-300', 'text-gray-600')}`}>
                    {session.questions_asked}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${theme('text-gray-300', 'text-gray-600')}`}>
                    {(session.accuracy * 100).toFixed(0)}%
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${theme('text-gray-400', 'text-gray-600')}`}>
                    {formatDate(session.started_at)}
                  </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => navigate(`/admin/sessions/${session.session_id}`)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        View
                      </button>
                      <button className={theme('text-gray-400 hover:text-gray-200', 'text-gray-600 hover:text-gray-900')}>
                        Export
                      </button>
                    </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Stats Summary */}
      <div className="mt-6 grid grid-cols-4 gap-4">
        <div className={`${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50')} rounded-lg p-4 ${theme('border', '')}`}>
          <div className={`text-sm ${theme('text-blue-300', 'text-blue-600')} font-medium`}>Avg. Theta</div>
          <div className={`text-2xl font-bold ${theme('text-blue-200', 'text-blue-900')} mt-1`}>
            {avgTheta}
          </div>
        </div>
        <div className={`${theme('bg-green-900/30 border-green-700', 'bg-green-50')} rounded-lg p-4 ${theme('border', '')}`}>
          <div className={`text-sm ${theme('text-green-300', 'text-green-600')} font-medium`}>Avg. Accuracy</div>
          <div className={`text-2xl font-bold ${theme('text-green-200', 'text-green-900')} mt-1`}>
            {avgAccuracy}%
          </div>
        </div>
        <div className={`${theme('bg-purple-900/30 border-purple-700', 'bg-purple-50')} rounded-lg p-4 ${theme('border', '')}`}>
          <div className={`text-sm ${theme('text-purple-300', 'text-purple-600')} font-medium`}>Avg. Questions</div>
          <div className={`text-2xl font-bold ${theme('text-purple-200', 'text-purple-900')} mt-1`}>
            {avgQuestions}
          </div>
        </div>
        <div className={`${theme('bg-orange-900/30 border-orange-700', 'bg-orange-50')} rounded-lg p-4 ${theme('border', '')}`}>
          <div className={`text-sm ${theme('text-orange-300', 'text-orange-600')} font-medium`}>Completion Rate</div>
          <div className={`text-2xl font-bold ${theme('text-orange-200', 'text-orange-900')} mt-1`}>
            {completionRate}%
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestSessions;