import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { theme } from '../../config/theme';
import config from '../../config/config';

import notificationService from '../../services/notificationService';

const Calibration = () => {
  const [itemBanks, setItemBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [calibratingBank, setCalibratingBank] = useState(null);
  const [error, setError] = useState(null);

  const API_BASE = config.API_BASE_URL;


  useEffect(() => {
    fetchItemBanks();
  }, []);

  const fetchItemBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/item-banks`);
      const data = await response.json();
      setItemBanks(data);
    } catch (err) {
      console.error('Failed to fetch item banks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCalibrate = async (itemBankName, numExaminees = 200, questionsPerExaminee = 15) => {
    if (!window.confirm(`Run calibration for "${itemBankName}"?\n\nThis will simulate ${numExaminees} test-takers with ${questionsPerExaminee} questions each and may take 1-2 minutes.`)) {
      return;
    }

    setCalibratingBank(itemBankName);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/item-banks/${itemBankName}/calibrate?n_examinees=${numExaminees}&questions_per=${questionsPerExaminee}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Calibration failed');
      }

      const data = await response.json();

      notificationService.success(`Calibration completed!\n\n${data.message}`);

      // Refresh item banks to show updated calibration status
      await fetchItemBanks();

    } catch (err) {
      setError(`Calibration failed for ${itemBankName}: ${err.message}`);
      notificationService.error(`Calibration failed: ${err.message}`);
    } finally {
      setCalibratingBank(null);
    }
  };

  const uncalibratedBanks = itemBanks.filter(b => b.status !== 'calibrated');
  const calibratedBanks = itemBanks.filter(b => b.status === 'calibrated');

  return (
    <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
      <div className="mb-8">
        <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>IRT Calibration</h1>
        <p className={theme('text-gray-400', 'text-gray-600')}>
          Run Item Response Theory calibration to estimate item parameters
        </p>
      </div>

      {error && (
        <div className={`mb-6 ${theme('bg-red-900/30 border-red-700 text-red-300', 'bg-red-50 border-red-200 text-red-700')} border px-4 py-3 rounded-lg`}>
          {error}
          <button onClick={() => setError(null)} className="float-right font-bold">×</button>
        </div>
      )}

      {/* Info Card */}
      <div className={`mb-8 ${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50 border-blue-200')} border rounded-lg p-6`}>
        <div className="flex items-start gap-4">
          <div className={`${theme('bg-blue-800/50', 'bg-blue-100')} p-3 rounded-lg`}>
            <svg className={`w-6 h-6 ${theme('text-blue-300', 'text-blue-600')}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className={`font-bold ${theme('text-blue-300', 'text-blue-900')} mb-2`}>About IRT Calibration</h3>
            <p className={`text-sm ${theme('text-blue-300', 'text-blue-800')} mb-2`}>
              Calibration estimates item parameters (discrimination, difficulty, guessing) using simulated test-taker responses.
              This process is essential for adaptive testing to work effectively.
            </p>
            <ul className={`text-sm ${theme('text-blue-300', 'text-blue-800')} list-disc list-inside space-y-1`}>
              <li>Simulates multiple test-takers at different ability levels</li>
              <li>Uses 3-parameter logistic (3PL) IRT model</li>
              <li>Updates item parameters based on response patterns</li>
              <li>Required before item bank can be used for assessments</li>
            </ul>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : itemBanks.length === 0 ? (
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-lg p-12 text-center`}>
          <div className="text-6xl mb-4">📦</div>
          <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>No Item Banks Found</h2>
          <p className={`${theme('text-gray-400', 'text-gray-600')} mb-6`}>
            You need to create and upload item banks before running calibration.
          </p>

          <Link
            to="/admin/upload"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition"
          >
            Upload Item Bank
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Uncalibrated Banks */}
          {uncalibratedBanks.length > 0 && (
            <div>
              <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>
                Needs Calibration ({uncalibratedBanks.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {uncalibratedBanks.map((bank) => (
                  <div key={bank.name} className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-lg p-6`}>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className={`text-lg font-bold ${theme('text-white', 'text-gray-900')}`}>{bank.display_name}</h3>
                        <p className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>{bank.subject}</p>
                      </div>
                      <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full">
                        Uncalibrated
                      </span>
                    </div>

                    <div className={`grid grid-cols-2 gap-4 mb-4 text-sm ${theme('text-gray-300', 'text-gray-600')}`}>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Items:</span> <span className="font-medium">{bank.total_items}</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Model:</span> <span className="font-medium">{bank.irt_model}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCalibrate(bank.name)}
                      disabled={calibratingBank === bank.name}
                      className={`w-full py-2.5 rounded-lg font-medium transition ${
                        calibratingBank === bank.name
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-blue-600 hover:bg-blue-700'
                      } text-white`}
                    >
                      {calibratingBank === bank.name ? (
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Calibrating...
                        </div>
                      ) : (
                        'Run Calibration'
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calibrated Banks */}
          {calibratedBanks.length > 0 && (
            <div>
              <h2 className={`text-xl font-bold ${theme('text-white', 'text-gray-900')} mb-4`}>
                Already Calibrated ({calibratedBanks.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {calibratedBanks.map((bank) => (
                  <div key={bank.name} className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-lg p-6`}>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className={`text-lg font-bold ${theme('text-white', 'text-gray-900')}`}>{bank.display_name}</h3>
                        <p className={`text-sm ${theme('text-gray-400', 'text-gray-600')}`}>{bank.subject}</p>
                      </div>
                      <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                        Calibrated
                      </span>
                    </div>

                    <div className={`grid grid-cols-3 gap-4 mb-4 text-sm ${theme('text-gray-300', 'text-gray-600')}`}>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Items:</span> <span className="font-medium">{bank.total_items}</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Tests:</span> <span className="font-medium">{bank.test_takers}</span>
                      </div>
                      <div>
                        <span className={theme('text-gray-400', 'text-gray-500')}>Accuracy:</span> <span className="font-medium">
                          {bank.accuracy ? `${(bank.accuracy * 100).toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCalibrate(bank.name)}
                      disabled={calibratingBank === bank.name}
                      className={`w-full py-2.5 rounded-lg font-medium transition ${
                        calibratingBank === bank.name
                          ? 'bg-gray-400 cursor-not-allowed'
                          : theme('bg-gray-700 hover:bg-gray-600', 'bg-gray-200 hover:bg-gray-300')
                      } ${theme('text-gray-300', 'text-gray-700')}`}
                    >
                      {calibratingBank === bank.name ? (
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                          Re-calibrating...
                        </div>
                      ) : (
                        'Re-calibrate'
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loading Overlay */}
      {calibratingBank && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white border-gray-200')} border rounded-lg p-6 max-w-sm`}>
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

export default Calibration;