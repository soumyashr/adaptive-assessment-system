import React, { useState, useEffect } from 'react';
import { theme } from '../../config/theme';

const ItemBanksPage = () => {
  const [itemBanks, setItemBanks] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadConfig, setUploadConfig] = useState({
    name: '',
    displayName: '',
    subject: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [calibratingBank, setCalibratingBank] = useState(null);

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

  const handleCreateAndUpload = async () => {
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
        `${API_BASE}/item-banks/${uploadConfig.name}/upload`,
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
      console.log(`Starting calibration for ${itemBankName}...`);

      const response = await fetch(
        `${API_BASE}/item-banks/${itemBankName}/calibrate?n_examinees=200&questions_per=15`,
        { method: 'POST' }
      );

      console.log('Calibration response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Calibration failed');
      }

      const data = await response.json();
      console.log('Calibration result:', data);

      alert(`Calibration completed!\n\n${data.message}\n\nStats updated successfully.`);
      await fetchItemBanks();

    } catch (err) {
      console.error('Calibration error:', err);
      setError(`Calibration failed: ${err.message}`);
      alert(`Calibration failed: ${err.message}`);
    } finally {
      setCalibratingBank(null);
    }
  };

  const getTotalItems = () => itemBanks.reduce((sum, b) => sum + b.total_items, 0);
  const getTotalTestTakers = () => itemBanks.reduce((sum, b) => sum + b.test_takers, 0);

  return (
    <div className={`min-h-screen ${theme('bg-gray-900', 'bg-gray-50')} p-6`}>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>Item Banks</h1>
          <p className={`${theme('text-gray-400', 'text-gray-600')} mt-1`}>Browse and manage your adaptive testing item banks</p>
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
        <div className={`${theme('bg-red-900/50 border-red-700 text-red-200', 'bg-red-50 border-red-200 text-red-700')} border px-4 py-3 rounded mb-6`}>
          {error}
          <button onClick={() => setError(null)} className="float-right font-bold">×</button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} p-6 rounded-lg shadow-lg border`}>
          <div className="flex items-center gap-3">
            <div className={`${theme('bg-blue-900/50', 'bg-blue-50')} p-3 rounded-lg`}>
              <svg className={`w-6 h-6 ${theme('text-blue-400', 'text-blue-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <div className={`${theme('text-gray-400', 'text-gray-600')} text-sm`}>Total Banks</div>
              <div className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{itemBanks.length}</div>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} p-6 rounded-lg shadow-lg border`}>
          <div className="flex items-center gap-3">
            <div className={`${theme('bg-orange-900/50', 'bg-orange-50')} p-3 rounded-lg`}>
              <svg className={`w-6 h-6 ${theme('text-orange-400', 'text-orange-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className={`${theme('text-gray-400', 'text-gray-600')} text-sm`}>Total Items</div>
              <div className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{getTotalItems()}</div>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} p-6 rounded-lg shadow-lg border`}>
          <div className="flex items-center gap-3">
            <div className={`${theme('bg-green-900/50', 'bg-green-50')} p-3 rounded-lg`}>
              <svg className={`w-6 h-6 ${theme('text-green-400', 'text-green-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div>
              <div className={`${theme('text-gray-400', 'text-gray-600')} text-sm`}>Test Takers</div>
              <div className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{getTotalTestTakers()}</div>
            </div>
          </div>
        </div>

        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} p-6 rounded-lg shadow-lg border`}>
          <div className="flex items-center gap-3">
            <div className={`${theme('bg-purple-900/50', 'bg-purple-50')} p-3 rounded-lg`}>
              <svg className={`w-6 h-6 ${theme('text-purple-400', 'text-purple-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div>
              <div className={`${theme('text-gray-400', 'text-gray-600')} text-sm`}>Active Jobs</div>
              <div className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')}`}>{calibratingBank ? '1' : '0'}</div>
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
            </div>
          </div>
        ))}

        {itemBanks.length === 0 && !loading && (
          <div className={`col-span-3 text-center py-12 ${theme('text-gray-400', 'text-gray-600')}`}>
            <p className="text-lg">No item banks yet. Click "Upload & Create" to create one.</p>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-lg p-8 w-full max-w-md border`}>
            <h2 className={`text-2xl font-bold mb-6 ${theme('text-white', 'text-gray-900')}`}>Upload & Create Item Bank</h2>

            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-1`}>
                  Item Bank Name*
                </label>
                <input
                  type="text"
                  placeholder="e.g., maths, vocabulary, physics"
                  className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                  value={uploadConfig.name}
                  onChange={(e) => setUploadConfig({...uploadConfig, name: e.target.value})}
                />
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>Used in URLs - no spaces, lowercase</p>
              </div>

              <div>
                <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-1`}>
                  Display Name*
                </label>
                <input
                  type="text"
                  placeholder="e.g., Mathematics, Vocabulary Assessment"
                  className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                  value={uploadConfig.displayName}
                  onChange={(e) => setUploadConfig({...uploadConfig, displayName: e.target.value})}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-1`}>
                  Subject*
                </label>
                <input
                  type="text"
                  placeholder="e.g., Mathematics, Vocabulary"
                  className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                  value={uploadConfig.subject}
                  onChange={(e) => setUploadConfig({...uploadConfig, subject: e.target.value})}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-1`}>
                  CSV File*
                </label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  className={`w-full ${theme('bg-gray-700 border-gray-600 text-white file:bg-blue-600 file:text-white', 'bg-white border-gray-300 text-gray-900 file:bg-blue-50 file:text-blue-700')} border rounded-lg px-4 py-2 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 hover:file:bg-blue-700`}
                />
                <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>
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
                className={`px-6 ${theme('bg-gray-700 hover:bg-gray-600 text-gray-200', 'bg-gray-200 hover:bg-gray-300 text-gray-700')} py-3 rounded-lg font-medium transition disabled:opacity-50`}
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
          <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} rounded-lg p-6 max-w-sm border`}>
            <div className="flex items-center gap-3 mb-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              <span className={`font-medium ${theme('text-white', 'text-gray-900')}`}>Calibrating {calibratingBank}...</span>
            </div>
            <p className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>
              This may take 1-2 minutes. Simulating 200 test-takers with 15 questions each...
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ItemBanksPage;