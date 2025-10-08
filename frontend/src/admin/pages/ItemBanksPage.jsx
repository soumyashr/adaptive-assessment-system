import React, { useState, useEffect } from 'react';

const ItemBanksPage = () => {
  const [itemBanks, setItemBanks] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedBank, setSelectedBank] = useState(null);
  const [deleteStats, setDeleteStats] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadConfig, setUploadConfig] = useState({
    name: '',
    displayName: '',
    subject: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [calibratingBank, setCalibratingBank] = useState(null);
  const [deletingBank, setDeletingBank] = useState(null);
  const [terminatingSession, setTerminatingSession] = useState(false);

  const API_BASE = 'http://localhost:8000/api';

  useEffect(() => {
    fetchItemBanks();
  }, []);

  const fetchItemBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/item-banks`);
      const data = await response.json();
      setItemBanks(data);
    } catch (err) {
      setError('Failed to load item banks');
      console.error(err);
    }
  };

  const handleDeleteClick = async (bank) => {
    setSelectedBank(bank);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/item-banks/${bank.name}/stats`);
      const stats = await response.json();
      setDeleteStats(stats);
      setShowDeleteModal(true);
    } catch (err) {
      setError('Failed to fetch item bank details');
      console.error(err);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedBank) return;

    setDeletingBank(selectedBank.name);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/item-banks/${selectedBank.name}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete item bank');
      }

      const result = await response.json();

      alert(`Successfully deleted ${selectedBank.display_name}\n\n` +
            `Removed:\n` +
            `• ${result.deleted.questions} questions\n` +
            `• ${result.deleted.test_takers} test sessions\n` +
            `• ${result.deleted.responses} responses`);

      setShowDeleteModal(false);
      setSelectedBank(null);
      setDeleteStats(null);
      fetchItemBanks();

    } catch (err) {
      setError(`Failed to delete: ${err.message}`);
      console.error(err);
    } finally {
      setDeletingBank(null);
    }
  };

  const handleTerminateSessions = async () => {
    if (!selectedBank) return;

    setTerminatingSession(true);
    setError(null);

    try {
      console.log('Terminating sessions for:', selectedBank.name);

      const response = await fetch(
        `${API_BASE}/item-banks/${selectedBank.name}/sessions/terminate`,
        {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to terminate sessions');
      }

      const result = await response.json();
      console.log('Terminate result:', result);

      alert(`Successfully terminated ${result.terminated_count} session(s)`);

      // Refresh stats to show updated active sessions count
      const statsResponse = await fetch(`${API_BASE}/item-banks/${selectedBank.name}/stats`);

      if (!statsResponse.ok) {
        throw new Error('Failed to refresh stats');
      }

      const newStats = await statsResponse.json();
      console.log('Updated stats:', newStats);
      setDeleteStats(newStats);

    } catch (err) {
      console.error('Error terminating sessions:', err);
      setError(`Failed to terminate sessions: ${err.message}`);
      alert(`Failed to terminate sessions: ${err.message}`);
    } finally {
      setTerminatingSession(false);
    }
  };

  const handleCreateAndUpload = async () => {
    const sanitizedName = uploadConfig.name
        .toLowerCase()
        .trim()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_-]/g, '');

    if (!sanitizedName || sanitizedName.length < 3) {
        alert('Item bank name must be at least 3 characters');
        return;
    }

    if (!uploadConfig.displayName.trim()) {
        alert('Display name is required');
        return;
    }
    if (!uploadConfig.subject.trim()) {
        alert('Subject is required');
        return;
    }
    if (!selectedFile || !uploadConfig.name) {
      alert('Please provide all required fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const createResponse = await fetch(
        `${API_BASE}/item-banks/create?name=${encodeURIComponent(uploadConfig.name)}&display_name=${encodeURIComponent(uploadConfig.displayName)}&subject=${encodeURIComponent(uploadConfig.subject)}`,
        {
          method: 'POST',
          headers: { 'accept': 'application/json' }
        }
      );

      if (!createResponse.ok) {
        const errorData = await createResponse.json();
        throw new Error(errorData.detail || 'Failed to create item bank');
      }

      const formData = new FormData();
      formData.append('file', selectedFile);

      const uploadResponse = await fetch(
        `${API_BASE}/item-banks/${sanitizedName}/upload`,
        {
          method: 'POST',
          body: formData
        }
      );

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        throw new Error(errorData.detail || 'Failed to upload questions');
      }

      const uploadData = await uploadResponse.json();
      alert(`Success! Imported ${uploadData.imported} questions`);

      setShowUploadModal(false);
      setUploadConfig({ name: '', displayName: '', subject: '' });
      setSelectedFile(null);
      fetchItemBanks();

    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCalibrate = async (itemBankName) => {
    if (!window.confirm(`Run calibration for ${itemBankName}? This will simulate 200 test-takers and take 1-2 minutes.`)) {
      return;
    }

    setCalibratingBank(itemBankName);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/item-banks/${itemBankName}/calibrate?n_examinees=200&questions_per=15`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Calibration failed');
      }

      const data = await response.json();
      alert(`Calibration completed!\n\n${data.message}\n\nStats updated successfully.`);
      await fetchItemBanks();

    } catch (err) {
      setError(`Calibration failed: ${err.message}`);
      alert(`Calibration failed: ${err.message}`);
    } finally {
      setCalibratingBank(null);
    }
  };

  const getTotalItems = () => itemBanks.reduce((sum, b) => sum + b.total_items, 0);
  const getTotalTestTakers = () => itemBanks.reduce((sum, b) => sum + b.test_takers, 0);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Item Banks</h1>
          <p className="text-gray-600 mt-1">Browse and manage your adaptive testing item banks</p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center gap-2 transition disabled:opacity-50"
        >
          <span className="text-xl">+</span> Upload & Create
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
          <button onClick={() => setError(null)} className="float-right font-bold">×</button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="bg-blue-50 p-3 rounded-lg">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <div className="text-gray-600 text-sm">Total Banks</div>
              <div className="text-3xl font-bold text-gray-900">{itemBanks.length}</div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="bg-orange-50 p-3 rounded-lg">
              <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className="text-gray-600 text-sm">Total Items</div>
              <div className="text-3xl font-bold text-gray-900">{getTotalItems()}</div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="bg-green-50 p-3 rounded-lg">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div>
              <div className="text-gray-600 text-sm">Test Takers</div>
              <div className="text-3xl font-bold text-gray-900">{getTotalTestTakers()}</div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="bg-purple-50 p-3 rounded-lg">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div>
              <div className="text-gray-600 text-sm">Active Jobs</div>
              <div className="text-3xl font-bold text-gray-900">{calibratingBank ? '1' : '0'}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Item Banks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {itemBanks.map((bank) => (
          <div key={bank.name} className="bg-gradient-to-br from-blue-600 to-purple-700 rounded-lg shadow-xl overflow-hidden">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="text-white">
                  <div className="text-sm opacity-80 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    {bank.subject}
                  </div>
                  <div className="text-xl font-bold mt-1">{bank.display_name}</div>
                  <div className="text-sm opacity-80">{bank.irt_model} Model • {bank.status}</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  bank.status === 'calibrated' 
                    ? 'bg-green-400 text-green-900' 
                    : 'bg-yellow-400 text-yellow-900'
                }`}>
                  {bank.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-white">
                <div>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <div className="text-xs opacity-80">Items</div>
                  </div>
                  <div className="text-lg font-bold">{bank.total_items}</div>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <div className="text-xs opacity-80">Takers</div>
                  </div>
                  <div className="text-lg font-bold">{bank.test_takers}</div>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <div className="text-xs opacity-80">Accuracy</div>
                  </div>
                  <div className="text-lg font-bold">
                    {bank.accuracy ? `${(bank.accuracy * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                    <div className="text-xs opacity-80">Responses</div>
                  </div>
                  <div className="text-lg font-bold">{bank.total_responses || 0}</div>
                </div>
              </div>
            </div>

            <div className="bg-white bg-opacity-10 p-4 flex gap-2">
              <button
                className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded transition font-medium text-sm"
                onClick={() => alert(`View details for ${bank.name} - Coming soon!`)}
              >
                View Details
              </button>
              <button
                className="px-4 bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded transition text-sm"
                onClick={() => window.open(`/student`, '_blank')}
              >
                Test
              </button>
              <button
                className={`px-4 bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded transition text-sm ${
                  calibratingBank === bank.name ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                onClick={() => handleCalibrate(bank.name)}
                disabled={calibratingBank === bank.name}
              >
                {calibratingBank === bank.name ? 'Calibrating...' : 'Calibrate'}
              </button>
              <button
                className={`px-4 bg-red-500 bg-opacity-50 hover:bg-opacity-70 text-white rounded transition text-sm ${
                  deletingBank === bank.name ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                onClick={() => handleDeleteClick(bank)}
                disabled={deletingBank === bank.name}
                title="Delete Item Bank"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        ))}

        {itemBanks.length === 0 && !loading && (
          <div className="col-span-3 text-center py-12 text-gray-600">
            <p className="text-lg">No item banks yet. Click "Upload & Create" to create one.</p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedBank && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-lg border border-gray-200 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-red-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Confirm Deletion</h2>
            </div>

            <div className="mb-6">
              <p className="text-gray-700 mb-4">
                Are you sure you want to delete <strong>{selectedBank.display_name}</strong>?
                This action cannot be undone.
              </p>

              {deleteStats && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <p className="font-semibold text-gray-900 mb-3">This will permanently delete:</p>
                  <ul className="space-y-2 text-gray-700">
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span><strong>{deleteStats.total_items}</strong> questions</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span><strong>{deleteStats.test_takers}</strong> test sessions</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span><strong>{deleteStats.total_responses}</strong> student responses</span>
                    </li>
                  </ul>

                  {deleteStats.active_sessions > 0 && (
                    <>
                      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-yellow-800 text-sm">
                          <strong>Warning:</strong> There are {deleteStats.active_sessions} active session(s).
                          These must be terminated before deletion.
                        </p>
                      </div>

                      <button
                        onClick={handleTerminateSessions}
                        disabled={terminatingSession}
                        className="mt-3 w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {terminatingSession ? (
                          <span className="flex items-center justify-center gap-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Terminating...
                          </span>
                        ) : (
                          'Terminate Active Sessions'
                        )}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDeleteConfirm}
                disabled={deletingBank || (deleteStats && deleteStats.active_sessions > 0)}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deletingBank ? 'Deleting...' : 'Delete Item Bank'}
              </button>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setSelectedBank(null);
                  setDeleteStats(null);
                }}
                disabled={deletingBank}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 py-3 rounded-lg font-medium transition disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md border border-gray-200">
            <h2 className="text-2xl font-bold mb-6 text-gray-900">Upload & Create Item Bank</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Item Bank Name*
                </label>
                <input
                  type="text"
                  placeholder="e.g., maths, vocabulary, physics"
                  className="w-full bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={uploadConfig.name}
                  onChange={(e) => setUploadConfig({...uploadConfig, name: e.target.value})}
                />
                <p className="text-xs text-gray-500 mt-1">Used in URLs - no spaces, lowercase</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name*
                </label>
                <input
                  type="text"
                  placeholder="e.g., Mathematics, Vocabulary Assessment"
                  className="w-full bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={uploadConfig.displayName}
                  onChange={(e) => setUploadConfig({...uploadConfig, displayName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subject*
                </label>
                <input
                  type="text"
                  placeholder="e.g., Mathematics, Vocabulary"
                  className="w-full bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={uploadConfig.subject}
                  onChange={(e) => setUploadConfig({...uploadConfig, subject: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Excel File*
                </label>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Required columns: question, option_a, option_b, option_c, option_d, answer, tier, topic
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCreateAndUpload}
                disabled={loading || !selectedFile || !uploadConfig.name}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Uploading...' : 'Upload & Create'}
              </button>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadConfig({ name: '', displayName: '', subject: '' });
                  setSelectedFile(null);
                  setError(null);
                }}
                disabled={loading}
                className="px-6 bg-gray-200 hover:bg-gray-300 text-gray-700 py-3 rounded-lg font-medium transition disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {calibratingBank && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              <span className="font-medium text-gray-900">Calibrating {calibratingBank}...</span>
            </div>
            <p className="text-sm text-gray-600">
              This may take 1-2 minutes. Simulating 200 test-takers with 15 questions each...
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ItemBanksPage;