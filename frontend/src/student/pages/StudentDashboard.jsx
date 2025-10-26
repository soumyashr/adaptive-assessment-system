// src/student/pages/StudentDashboard.jsx
import React from 'react';
import { getThemeColors, DARK_MODE } from '../../config/theme';

const StudentDashboard = ({
  userStats,
  availableItemBanks,
  onStartAssessment,
  loading
}) => {
  const colors = getThemeColors();

  // Transform userStats into progress data
  const progress = userStats?.proficiencies || [];

  // Transform availableItemBanks into assessments
  const availableAssessments = availableItemBanks
    .filter(bank => bank.status === 'calibrated')
    .map(bank => ({
      id: bank.name,
      name: bank.display_name,
      questions: bank.total_items,
      calibrated: true
    }));

  const handleStartAssessment = (assessmentId) => {
    onStartAssessment(assessmentId);
  };

  const getThetaTierLabel = (theta) => {
    if (theta < -1.0) return 'Beginner';
    if (theta < 0.0) return 'Intermediate';
    if (theta < 1.0) return 'Advanced';
    return 'Expert';
  };

  const getTierColor = (theta) => {
    if (theta < -1.0) return '#EF4444';
    if (theta < 0.0) return '#F59E0B';
    if (theta < 1.0) return '#10B981';
    return '#3B82F6';
  };

  return (
    <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        marginBottom: '32px',
        background: colors.cardBg,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: '12px',
        padding: '24px',
        boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)'
      }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: 'bold',
          color: colors.textPrimary,
          marginBottom: '8px'
        }}>
          Your Assessment Dashboard
        </h1>
        <p style={{
          color: colors.textMuted,
          fontSize: '14px',
          margin: 0
        }}>
          Track your progress and start new assessments
        </p>
      </div>

      {/* Theta Score Guide */}
      <div style={{
        background: colors.cardBg,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: '12px',
        padding: '28px',
        marginBottom: '32px',
        boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '20px'
        }}>
          <span style={{ fontSize: '24px' }}>📊</span>
          <h3 style={{
            fontSize: '18px',
            fontWeight: '600',
            color: colors.textPrimary,
            margin: 0
          }}>
            Understanding Your Theta (θ) Score
          </h3>
        </div>

        {/* Gradient Bar */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{
            height: '12px',
            borderRadius: '6px',
            background: 'linear-gradient(to right, #EF4444 0%, #EF4444 33.33%, #F59E0B 33.33%, #F59E0B 50%, #10B981 50%, #10B981 66.66%, #3B82F6 66.66%, #3B82F6 100%)',
            position: 'relative',
            boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)'
          }}>
            {/* Tick marks */}
            {[-3, -1, 0, 1, 3].map((val, idx) => (
              <div
                key={val}
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: `${(idx / 4) * 100}%`,
                  transform: 'translateX(-50%)',
                  marginTop: '8px',
                  fontSize: '12px',
                  color: colors.textMuted,
                  fontWeight: '600'
                }}
              >
                {val > 0 ? '+' : ''}{val === 0 ? '0' : val}
              </div>
            ))}
          </div>
        </div>

        {/* Labels */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          marginTop: '36px',
          marginBottom: '16px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#EF4444',
              marginBottom: '6px'
            }}>
              Beginner
            </div>
            <div style={{
              fontSize: '13px',
              color: colors.textMuted
            }}>
              -3.0 to -1.0
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#F59E0B',
              marginBottom: '6px'
            }}>
              Intermediate
            </div>
            <div style={{
              fontSize: '13px',
              color: colors.textMuted
            }}>
              -1.0 to 0.0
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#10B981',
              marginBottom: '6px'
            }}>
              Advanced
            </div>
            <div style={{
              fontSize: '13px',
              color: colors.textMuted
            }}>
              0.0 to +1.0
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#3B82F6',
              marginBottom: '6px'
            }}>
              Expert
            </div>
            <div style={{
              fontSize: '13px',
              color: colors.textMuted
            }}>
              +1.0 to +3.0
            </div>
          </div>
        </div>

        {/* Explanation */}
        <p style={{
          fontSize: '14px',
          color: colors.textMuted,
          margin: 0,
          textAlign: 'center',
          lineHeight: '1.6'
        }}>
          Your θ score improves as you answer questions correctly. Higher scores indicate stronger ability.
        </p>
      </div>

      {/* Your Progress Section */}
      <div style={{ marginBottom: '40px' }}>
        <h2 style={{
          fontSize: '14px',
          fontWeight: '600',
          color: colors.textMuted,
          marginBottom: '16px',
          textTransform: 'uppercase',
          letterSpacing: '0.8px'
        }}>
          Your Progress
        </h2>

        {progress.length === 0 ? (
          <div style={{
            background: colors.cardBg,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: '12px',
            padding: '32px',
            textAlign: 'center',
            boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)'
          }}>
            <p style={{
              color: colors.textMuted,
              fontSize: '14px',
              margin: 0
            }}>
              No completed assessments yet
            </p>
          </div>
        ) : (
          <div style={{
            background: colors.cardBg,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)'
          }}>
            {progress.map((item, index) => (
              <div
                key={index}
                style={{
                  padding: '20px 24px',
                  borderBottom: index < progress.length - 1 ? `1px solid ${colors.cardBorder}` : 'none',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'background 0.2s',
                  background: 'transparent'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = DARK_MODE ? 'rgba(255,255,255,0.03)' : '#F9FAFB';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                <div style={{ flex: 1 }}>
                  <span style={{
                    fontSize: '15px',
                    fontWeight: '600',
                    color: colors.textPrimary,
                    textTransform: 'capitalize'
                  }}>
                    {item.item_bank}
                  </span>
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px'
                }}>
                  {/* Level Badge - Outline Style */}
                  <span style={{
                    padding: '6px 16px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '600',
                    border: `1.5px solid ${getTierColor(item.theta)}`,
                    background: 'transparent',
                    color: getTierColor(item.theta)
                  }}>
                    {getThetaTierLabel(item.theta)}
                  </span>
                  {/* Theta Score - Subtle Badge */}
                  <span style={{
                    padding: '6px 16px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '600',
                    background: DARK_MODE ? 'rgba(255,255,255,0.05)' : '#F3F4F6',
                    color: colors.textPrimary,
                    fontFamily: 'monospace',
                    minWidth: '80px',
                    textAlign: 'center'
                  }}>
                    θ: {item.theta.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available Assessments Section */}
      <div>
        <h2 style={{
          fontSize: '14px',
          fontWeight: '600',
          color: colors.textMuted,
          marginBottom: '16px',
          textTransform: 'uppercase',
          letterSpacing: '0.8px'
        }}>
          Available Assessments
        </h2>

        {availableAssessments.length === 0 ? (
          <div style={{
            background: colors.cardBg,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: '12px',
            padding: '48px',
            textAlign: 'center',
            boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)'
          }}>
            <p style={{
              color: colors.textMuted,
              fontSize: '14px',
              margin: 0
            }}>
              No assessments available at the moment
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '20px'
          }}>
            {availableAssessments.map((assessment, index) => {
              const isLastOdd = availableAssessments.length % 2 !== 0 && index === availableAssessments.length - 1;

              return (
                <div
                  key={assessment.id}
                  style={{
                    background: colors.cardBg,
                    border: `1px solid ${colors.cardBorder}`,
                    borderRadius: '12px',
                    padding: '28px',
                    boxShadow: DARK_MODE ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.08)',
                    transition: 'all 0.2s ease',
                    cursor: 'pointer',
                    gridColumn: isLastOdd ? '1 / -1' : 'auto',
                    maxWidth: isLastOdd ? '50%' : '100%',
                    margin: isLastOdd ? '0 auto' : '0',
                    width: isLastOdd ? '100%' : 'auto'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = DARK_MODE
                      ? '0 4px 12px rgba(0, 0, 0, 0.3)'
                      : '0 4px 12px rgba(0, 0, 0, 0.12)';
                    e.currentTarget.style.borderColor = colors.primary;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = DARK_MODE
                      ? 'none'
                      : '0 1px 3px rgba(0, 0, 0, 0.08)';
                    e.currentTarget.style.borderColor = colors.cardBorder;
                  }}
                >
                  <div style={{ marginBottom: '20px' }}>
                    <h3 style={{
                      fontSize: '18px',
                      fontWeight: '600',
                      color: colors.textPrimary,
                      marginBottom: '8px',
                      lineHeight: '1.4'
                    }}>
                      {assessment.name}
                    </h3>
                    <p style={{
                      fontSize: '14px',
                      color: colors.textMuted,
                      marginBottom: '10px',
                      margin: 0
                    }}>
                      {assessment.questions} questions
                    </p>
                    {assessment.calibrated && (
                      <span style={{
                        display: 'inline-block',
                        marginTop: '10px',
                        padding: '4px 12px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: '600',
                        background: DARK_MODE ? 'rgba(16, 185, 129, 0.15)' : '#D1FAE5',
                        color: '#10B981'
                      }}>
                        Calibrated
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => handleStartAssessment(assessment.id)}
                    disabled={loading}
                    style={{
                      width: '100%',
                      padding: '12px 24px',
                      borderRadius: '8px',
                      border: 'none',
                      background: colors.primary,
                      color: 'white',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s',
                      opacity: loading ? 0.6 : 1
                    }}
                    onMouseEnter={(e) => {
                      if (!loading) {
                        e.currentTarget.style.background = '#059669';
                        e.currentTarget.style.transform = 'scale(1.02)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = colors.primary;
                      e.currentTarget.style.transform = 'scale(1)';
                    }}
                  >
                    {loading ? 'Loading...' : 'Start Assessment'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentDashboard;