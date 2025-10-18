import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getThemeColors, DARK_MODE } from '../../config/theme';
import config from '../../config/config';
import notificationService from '../../services/notificationService';

const Calibration = () => {
  const [itemBanks, setItemBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [calibratingBank, setCalibratingBank] = useState(null);
  const [error, setError] = useState(null);

  const colors = getThemeColors();
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
    <div className="p-8 min-h-screen" style={{ backgroundColor: colors.bgSecondary }}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2" style={{ color: colors.textPrimary }}>
          IRT Calibration
        </h1>
        <p style={{ color: colors.textMuted }}>
          Run Item Response Theory calibration to estimate item parameters
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div
          className="mb-6 border px-4 py-3 rounded-lg"
          style={{
            backgroundColor: colors.errorBg,
            borderColor: colors.error,
            color: colors.error
          }}
        >
          {error}
          <button onClick={() => setError(null)} className="float-right font-bold">×</button>
        </div>
      )}

      {/* Info Card - Theme Aware */}
      <div
        className="mb-8 rounded-xl p-6"
        style={{
          backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
        }}
      >
        <div className="flex items-start gap-4">
          {/* Icon Circle */}
          <div
            className="p-4 rounded-2xl flex-shrink-0"
            style={{
              backgroundColor: colors.success,
            }}
          >
            <svg
              className="w-7 h-7"
              style={{ color: 'white' }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3
              className="font-bold mb-2 text-lg"
              style={{ color: colors.textPrimary }}
            >
              About IRT Calibration
            </h3>
            <p
              className="text-sm mb-3 leading-relaxed"
              style={{ color: colors.textSecondary }}
            >
              Calibration estimates item parameters (discrimination, difficulty, guessing) using simulated test-taker responses.
              This process is essential for adaptive testing to work effectively.
            </p>
            <ul
              className="text-sm space-y-2"
              style={{ color: colors.textSecondary }}
            >
              <li className="flex items-start">
                <span className="mr-2" style={{ color: colors.success }}>✓</span>
                <span>Simulates multiple test-takers at different ability levels</span>
              </li>
              <li className="flex items-start">
                <span className="mr-2" style={{ color: colors.success }}>✓</span>
                <span>Uses 3-parameter logistic (3PL) IRT model</span>
              </li>
              <li className="flex items-start">
                <span className="mr-2" style={{ color: colors.success }}>✓</span>
                <span>Updates item parameters based on response patterns</span>
              </li>
              <li className="flex items-start">
                <span className="mr-2" style={{ color: colors.success }}>✓</span>
                <span>Required before item bank can be used for assessments</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div
            className="animate-spin rounded-full h-12 w-12 border-b-2"
            style={{ borderColor: colors.primary }}
          ></div>
        </div>
      ) : itemBanks.length === 0 ? (
        <div
          className="rounded-xl p-12 text-center"
          style={{
            backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
          }}
        >
          <div className="text-6xl mb-4">📦</div>
          <h2
            className="text-xl font-bold mb-2"
            style={{ color: colors.textPrimary }}
          >
            No Item Banks Found
          </h2>
          <p
            className="mb-6"
            style={{ color: colors.textMuted }}
          >
            You need to create and upload item banks before running calibration.
          </p>

          <Link
            to="/admin/upload"
            className="inline-block px-6 py-3 rounded-lg font-medium transition"
            style={{
              background: 'linear-gradient(135deg, #fbbf24 0%, #10b981 100%)',
              color: 'white',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          >
            Upload Item Bank
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Uncalibrated Banks */}
          {uncalibratedBanks.length > 0 && (
            <div>
              <h2
                className="text-xl font-bold mb-4"
                style={{ color: colors.textPrimary }}
              >
                Needs Calibration ({uncalibratedBanks.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {uncalibratedBanks.map((bank) => (
                  <div
                    key={bank.name}
                    className="rounded-xl p-6 hover:shadow-lg transition-all"
                    style={{
                      backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
                      border: '2px solid #fbbf24',
                      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
                    }}
                  >
                    <div className="flex items-start gap-4 mb-4">
                      {/* Icon */}
                      <div
                        className="p-3 rounded-xl flex-shrink-0"
                        style={{ backgroundColor: colors.secondary }}
                      >
                        <svg
                          className="w-6 h-6"
                          style={{ color: 'white' }}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                      </div>

                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-1">
                          <h3
                            className="text-lg font-bold"
                            style={{ color: colors.textPrimary }}
                          >
                            {bank.display_name}
                          </h3>
                          <span
                            className="px-3 py-1 text-xs font-semibold rounded-full"
                            style={{
                              backgroundColor: colors.warningBg,
                              color: colors.warning
                            }}
                          >
                            Uncalibrated
                          </span>
                        </div>
                        <p
                          className="text-sm mb-3"
                          style={{ color: colors.textMuted }}
                        >
                          {bank.subject}
                        </p>
                      </div>
                    </div>

                    <div
                      className="grid grid-cols-2 gap-4 mb-4 text-sm"
                      style={{ color: colors.textSecondary }}
                    >
                      <div>
                        <span style={{ color: colors.textMuted }}>Items:</span>{' '}
                        <span className="font-semibold" style={{ color: colors.textPrimary }}>{bank.total_items}</span>
                      </div>
                      <div>
                        <span style={{ color: colors.textMuted }}>Model:</span>{' '}
                        <span className="font-semibold" style={{ color: colors.textPrimary }}>{bank.irt_model}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCalibrate(bank.name)}
                      disabled={calibratingBank === bank.name}
                      className={`w-full py-3 rounded-lg font-medium transition ${
                        calibratingBank === bank.name
                          ? 'opacity-50 cursor-not-allowed'
                          : ''
                      }`}
                      style={{
                        background: calibratingBank === bank.name
                          ? colors.border
                          : 'linear-gradient(135deg, #fbbf24 0%, #10b981 100%)',
                        color: 'white',
                        boxShadow: calibratingBank === bank.name ? 'none' : '0 2px 4px rgba(0, 0, 0, 0.1)'
                      }}
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
              <h2
                className="text-xl font-bold mb-4"
                style={{ color: colors.textPrimary }}
              >
                Already Calibrated ({calibratedBanks.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {calibratedBanks.map((bank) => (
                  <div
                    key={bank.name}
                    className="rounded-xl p-6 hover:shadow-lg transition-shadow"
                    style={{
                      backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
                      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
                    }}
                  >
                    <div className="flex items-start gap-4 mb-4">
                      {/* Icon */}
                      <div
                        className="p-3 rounded-xl flex-shrink-0"
                        style={{ backgroundColor: colors.success }}
                      >
                        <svg
                          className="w-6 h-6"
                          style={{ color: 'white' }}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>

                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-1">
                          <h3
                            className="text-lg font-bold"
                            style={{ color: colors.textPrimary }}
                          >
                            {bank.display_name}
                          </h3>
                          <span
                            className="px-3 py-1 text-xs font-semibold rounded-full"
                            style={{
                              backgroundColor: colors.successBg,
                              color: colors.success
                            }}
                          >
                            Calibrated
                          </span>
                        </div>
                        <p
                          className="text-sm mb-3"
                          style={{ color: colors.textMuted }}
                        >
                          {bank.subject}
                        </p>
                      </div>
                    </div>

                    <div
                      className="grid grid-cols-3 gap-4 mb-4 text-sm"
                      style={{ color: colors.textSecondary }}
                    >
                      <div>
                        <span style={{ color: colors.textMuted }}>Items:</span>{' '}
                        <span className="font-semibold" style={{ color: colors.textPrimary }}>{bank.total_items}</span>
                      </div>
                      <div>
                        <span style={{ color: colors.textMuted }}>Tests:</span>{' '}
                        <span className="font-semibold" style={{ color: colors.textPrimary }}>{bank.test_takers}</span>
                      </div>
                      <div>
                        <span style={{ color: colors.textMuted }}>Accuracy:</span>{' '}
                        <span className="font-semibold" style={{ color: colors.textPrimary }}>
                          {bank.accuracy ? `${(bank.accuracy * 100).toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCalibrate(bank.name)}
                      disabled={calibratingBank === bank.name}
                      className={`w-full py-3 rounded-lg font-medium transition ${
                        calibratingBank === bank.name
                          ? 'opacity-50 cursor-not-allowed'
                          : ''
                      }`}
                      style={{
                        backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
                        color: colors.success,
                        border: `2px solid ${colors.success}`,
                      }}
                    >
                      {calibratingBank === bank.name ? (
                        <div className="flex items-center justify-center gap-2">
                          <div
                            className="animate-spin rounded-full h-4 w-4 border-b-2"
                            style={{ borderColor: colors.success }}
                          ></div>
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            className="rounded-xl p-6 max-w-sm"
            style={{
              backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className="animate-spin rounded-full h-6 w-6 border-b-2"
                style={{ borderColor: colors.primary }}
              ></div>
              <span
                className="font-medium"
                style={{ color: colors.textPrimary }}
              >
                Calibrating {calibratingBank}...
              </span>
            </div>
            <p
              className="text-sm"
              style={{ color: colors.textMuted }}
            >
              This may take 1-2 minutes. Simulating 200 test-takers with 15 questions each...
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Calibration;