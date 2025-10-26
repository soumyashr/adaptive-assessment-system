// src/admin/pages/ItemBanksPage.jsx
import React, { useState, useEffect } from 'react';
import config from '../../config/config';
import { getThemeColors, DARK_MODE } from '../../config/theme';
import { Database, Users, FileText, Activity, Trash2, Play, Settings } from 'lucide-react';
import notificationService from '../../services/notificationService';

const ItemBanksPage = () => {
  const [itemBanks, setItemBanks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [calibratingBank, setCalibratingBank] = useState(null);

  // Delete functionality states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedBank, setSelectedBank] = useState(null);
  const [deleteStats, setDeleteStats] = useState(null);
  const [deletingBank, setDeletingBank] = useState(false);

  const API_BASE = config.API_BASE_URL;
  const colors = getThemeColors();

  useEffect(() => {
    fetchItemBanks();
  }, []);

  const fetchItemBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/item-banks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setItemBanks(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Fetch error:', err);
      setError(`Failed to load: ${err.message}`);
      setItemBanks([]);
    }
  };

  const handleCalibrate = async (itemBankName) => {
    if (!window.confirm(`Run calibration for ${itemBankName}?`)) return;

    setCalibratingBank(itemBankName);
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
      notificationService.success(`Calibration completed!\n\n${data.message}`);
      await fetchItemBanks();
    } catch (err) {
      setError(`Calibration failed: ${err.message}`);
      notificationService.error(`Calibration failed: ${err.message}`);
    } finally {
      setCalibratingBank(null);
    }
  };

  // Delete functionality handlers
  const handleDeleteClick = async (bank) => {
    setSelectedBank(bank);
    setShowDeleteModal(true);

    try {
      const response = await fetch(`${API_BASE}/item-banks/${bank.name}/stats`);
      const stats = await response.json();
      setDeleteStats(stats);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
      setDeleteStats(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedBank) return;

    setDeletingBank(true);

    try {
      const response = await fetch(
        `${API_BASE}/item-banks/${selectedBank.name}`,
        { method: 'DELETE' }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to delete item bank');
      }

      notificationService.success(`Successfully deleted ${selectedBank.display_name}`);
      setShowDeleteModal(false);
      setSelectedBank(null);
      setDeleteStats(null);
      await fetchItemBanks();

    } catch (error) {
      console.error('Error deleting item bank:', error);
      notificationService.error(`Error: ${error.message}`);
      setShowDeleteModal(false);
      setSelectedBank(null);
      setDeleteStats(null);
    } finally {
      setDeletingBank(false);
    }
  };

  const getTotalItems = () => itemBanks.reduce((sum, b) => sum + (b?.total_items || 0), 0);
  const getTotalTestTakers = () => itemBanks.reduce((sum, b) => sum + (b?.test_takers || 0), 0);

  const StatBadge = ({ icon: Icon, label, value, color }) => (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 10px',
      background: DARK_MODE ? `${color}20` : `${color}15`,
      borderRadius: '6px',
      flex: 1
    }}>
      <Icon size={14} color={color} />
      <div>
        <div style={{ fontSize: '10px', color: colors.textMuted, lineHeight: '1' }}>
          {label}
        </div>
        <div style={{ fontSize: '16px', fontWeight: 'bold', color: colors.textPrimary, lineHeight: '1.2', marginTop: '2px' }}>
          {value}
        </div>
      </div>
    </div>
  );

  const HeaderStatCard = ({ icon: Icon, label, value, color }) => (
    <div style={{
      background: colors.cardBg,
      border: `1px solid ${colors.cardBorder}`,
      borderRadius: '10px',
      padding: '16px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flex: 1
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
        className="mb-8 rounded-xl p-6"
        style={{
          backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
        }}
      >
        <h1 className="text-3xl font-bold mb-2" style={{ color: colors.textPrimary }}>
          Item Banks
        </h1>
        <p style={{ color: colors.textMuted }}>
          Browse and manage your adaptive testing item banks
        </p>
      </div>



      {/* Header Stats Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <HeaderStatCard
          icon={Database}
          label="Total Banks"
          value={itemBanks.length}
          color="#EAB308"
        />
        <HeaderStatCard
          icon={FileText}
          label="Total Items"
          value={getTotalItems()}
          color="#10B981"
        />
        <HeaderStatCard
          icon={Users}
          label="Test Takers"
          value={getTotalTestTakers()}
          color="#3B82F6"
        />
        <HeaderStatCard
          icon={Settings}
          label="Running Jobs"
          value={calibratingBank ? 1 : 0}
          color="#8B5CF6"
        />
      </div>

      {/* Error Message */}
      {error && (
        <div style={{
          marginBottom: '16px',
          padding: '12px 16px',
          background: colors.errorBg,
          border: `1px solid ${colors.error}`,
          borderRadius: '8px',
          color: colors.error,
          fontSize: '14px'
        }}>
          {error}
        </div>
      )}

      {/* Item Banks Grid - Smaller Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
        gap: '14px'
      }}>
        {itemBanks.map((bank) => (
          <div
            key={bank.name}
            style={{
              background: colors.cardBg,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: '10px',
              padding: '16px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {/* Header */}
            <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
              <div>
                <div style={{ fontSize: '10px', color: colors.textMuted, marginBottom: '3px' }}>
                  {bank.subject}
                </div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '2px' }}>
                  {bank.display_name}
                </div>
                <div style={{ fontSize: '11px', color: colors.textMuted }}>
                  {bank.irt_model} Model
                </div>
              </div>
              <div style={{
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '10px',
                fontWeight: '600',
                background: bank.status === 'calibrated' ? colors.successBg : colors.warningBg,
                color: bank.status === 'calibrated' ? colors.success : colors.warning
              }}>
                {bank.status}
              </div>
            </div>

            {/* Stats Grid - 2x2 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '6px',
              marginBottom: '12px'
            }}>
              <StatBadge icon={FileText} label="Items" value={bank.total_items || 0} color="#10B981" />
              <StatBadge icon={Users} label="Takers" value={bank.test_takers || 0} color="#3B82F6" />
              <StatBadge
                icon={Activity}
                label="Accuracy"
                value={bank.accuracy ? `${(bank.accuracy * 100).toFixed(0)}%` : 'N/A'}
                color="#8B5CF6"
              />
              <StatBadge icon={Database} label="Responses" value={bank.total_responses || 0} color="#F59E0B" />
            </div>

            {/* Action Buttons - Compact */}
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => notificationService.notify(`View details for ${bank.name}`)}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '6px',
                  border: 'none',
                  background: colors.primary,
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px'
                }}
              >
                <Database size={14} />
                Details
              </button>
              <button
                onClick={() => window.open('/student', '_blank')}
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.cardBorder}`,
                  background: colors.cardBg,
                  color: colors.textPrimary,
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Play size={14} />
                Test
              </button>
              <button
                onClick={() => handleCalibrate(bank.name)}
                disabled={calibratingBank === bank.name}
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.cardBorder}`,
                  background: colors.cardBg,
                  color: colors.textPrimary,
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: calibratingBank === bank.name ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  opacity: calibratingBank === bank.name ? 0.5 : 1
                }}
              >
                <Settings size={14} />
                Cal
              </button>
              <button
                onClick={() => handleDeleteClick(bank)}
                style={{
                  padding: '8px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.error}`,
                  background: `${colors.error}15`,
                  color: colors.error,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {!loading && itemBanks.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '60px 20px',
          color: colors.textMuted
        }}>
          <Database size={48} color={colors.textMuted} style={{ margin: '0 auto 16px' }} />
          <p style={{ fontSize: '16px', marginBottom: '8px' }}>No item banks yet</p>
          <p style={{ fontSize: '14px' }}>Click "Upload & Create" to create your first item bank</p>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedBank && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: colors.cardBg,
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: `${colors.error}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Trash2 size={24} color={colors.error} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '4px' }}>
                  Confirm Deletion
                </h3>
                <p style={{ fontSize: '14px', color: colors.textMuted }}>
                  This action cannot be undone
                </p>
              </div>
            </div>

            <p style={{ color: colors.textSecondary, marginBottom: '16px' }}>
              Are you sure you want to delete <strong>{selectedBank.display_name}</strong>?
            </p>

            {deleteStats ? (
              <>
                {deleteStats.active_sessions > 0 ? (
                  <>
                      <div style={{
                        padding: '12px',
                        borderRadius: '8px',
                        background: `${colors.warning}20`,
                        border: `1px solid ${colors.warning}`,
                        marginBottom: '12px'
                      }}>
                        <p style={{ color: colors.warning, fontWeight: 'bold', marginBottom: '8px' }}>
                          ⚠️ Warning: {deleteStats.active_sessions} active session(s)
                        </p>
                        <p style={{ fontSize: '13px', color: colors.textSecondary }}>
                          There are ongoing assessments. These must be completed before deletion.
                        </p>
                      </div>

                      <button
                        onClick={async () => {
                          try {
                            const response = await fetch(
                              `${API_BASE}/item-banks/${selectedBank.name}/sessions/terminate`,
                              { method: 'POST' }
                            );

                            if (response.ok) {
                              const result = await response.json();
                              notificationService.success(
                                `Successfully terminated ${result.terminated_count} session(s)`
                              );

                              const statsResponse = await fetch(
                                `${API_BASE}/item-banks/${selectedBank.name}/stats`
                              );
                              const newStats = await statsResponse.json();
                              setDeleteStats(newStats);
                            } else {
                              const errorData = await response.json();
                              notificationService.error(
                                `Failed to terminate sessions: ${errorData.detail || 'Unknown error'}`
                              );
                            }
                          } catch (err) {
                            console.error('Error terminating sessions:', err);
                            notificationService.error('Error terminating sessions');
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '10px 16px',
                          borderRadius: '8px',
                          border: 'none',
                          background: colors.warning,
                          color: 'white',
                          fontWeight: '600',
                          fontSize: '14px',
                          cursor: 'pointer',
                          marginBottom: '16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px'
                        }}
                      >
                        Terminate Active Sessions
                      </button>
                    </>
                ) : (
                  <div style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: colors.bgSecondary,
                    marginBottom: '16px'
                  }}>
                    <p style={{ fontSize: '14px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '8px' }}>
                      This will permanently delete:
                    </p>
                    <ul style={{ fontSize: '13px', color: colors.textSecondary, paddingLeft: '20px' }}>
                      <li>✗ {deleteStats.total_items} questions</li>
                      <li>✗ {deleteStats.test_takers} test sessions</li>
                      <li>✗ {deleteStats.total_responses} student responses</li>
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  border: `3px solid ${colors.border}`,
                  borderTopColor: colors.primary,
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto'
                }} />
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setSelectedBank(null);
                  setDeleteStats(null);
                }}
                disabled={deletingBank}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: `1px solid ${colors.cardBorder}`,
                  background: colors.cardBg,
                  color: colors.textPrimary,
                  fontWeight: '600',
                  cursor: deletingBank ? 'not-allowed' : 'pointer',
                  opacity: deletingBank ? 0.5 : 1
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deletingBank || (deleteStats && deleteStats.active_sessions > 0)}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  background: (deleteStats && deleteStats.active_sessions > 0) ? colors.border : colors.error,
                  color: 'white',
                  fontWeight: '600',
                  cursor: (deletingBank || (deleteStats && deleteStats.active_sessions > 0)) ? 'not-allowed' : 'pointer',
                  opacity: (deletingBank || (deleteStats && deleteStats.active_sessions > 0)) ? 0.5 : 1
                }}
              >
                {deletingBank ? 'Deleting...' : 'Delete Item Bank'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Add CSS for spinner animation
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

export default ItemBanksPage;