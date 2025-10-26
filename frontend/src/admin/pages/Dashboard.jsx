


// ============================================
// 3. src/admin/pages/Dashboard.jsx - OPTIMIZED
// ============================================
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getThemeColors, DARK_MODE } from '../../config/theme';
import { Database, FileText, Users, TrendingUp, Upload, Settings, Activity } from 'lucide-react';
import config from '../../config/config';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalBanks: 0,
    totalItems: 0,
    totalTestTakers: 0,
    totalSessions: 0
  });
  const [loading, setLoading] = useState(true);
  const colors = getThemeColors();
  const API_BASE = config.API_BASE_URL;

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const banksResponse = await fetch(`${API_BASE}/item-banks`);
      const banksData = await banksResponse.json();
      const banks = Array.isArray(banksData) ? banksData : [];

      const sessionsResponse = await fetch(`${API_BASE}/sessions`);
      const sessionsData = await sessionsResponse.json();
      const sessions = Array.isArray(sessionsData) ? sessionsData : [];

      const uniqueUsers = new Set(sessions.map(s => s.username)).size;

      setStats({
        totalBanks: banks.length,
        totalItems: banks.reduce((sum, b) => sum + (b?.total_items || 0), 0),
        totalTestTakers: uniqueUsers,
        totalSessions: sessions.length
      });
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, label, value, color, detail }) => (
    <div style={{
      background: colors.cardBg,
      border: `1px solid ${colors.cardBorder}`,
      borderRadius: '12px',
      padding: '20px',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'pointer'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'none';
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '12px',
        background: color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon size={28} color="white" />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '13px', color: colors.textMuted, marginBottom: '4px' }}>
          {label}
        </div>
        <div style={{ fontSize: '28px', fontWeight: 'bold', color: colors.textPrimary }}>
          {value}
        </div>
        {detail && (
          <div style={{ fontSize: '12px', color: colors.textMuted, marginTop: '4px' }}>
            {detail}
          </div>
        )}
      </div>
    </div>
  );

  const QuickAction = ({ to, icon: Icon, label, color }) => (
    <Link
      to={to}
      style={{
        border: `2px dashed ${colors.cardBorder}`,
        borderRadius: '12px',
        padding: '24px',
        textAlign: 'center',
        textDecoration: 'none',
        display: 'block',
        background: colors.cardBg,
        transition: 'all 0.2s'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.background = `${color}10`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = colors.cardBorder;
        e.currentTarget.style.background = colors.cardBg;
      }}
    >
      <Icon size={32} color={color} style={{ margin: '0 auto 12px', display: 'block' }} />
      <div style={{ fontWeight: '600', fontSize: '14px', color: colors.textPrimary }}>
        {label}
      </div>
    </Link>
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
          Dashboard
        </h1>
        <p style={{ color: colors.textMuted }}>
         Overview of your adaptive testing system
        </p>
      </div>

      {/* Stats Grid - 4 columns */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <StatCard
          icon={Database}
          label="Item Banks"
          value={stats.totalBanks}
          color="#EAB308"
          detail="Active"
        />
        <StatCard
          icon={FileText}
          label="Total Items"
          value={stats.totalItems}
          color="#10B981"
          detail="Across all banks"
        />
        <StatCard
          icon={Users}
          label="Test Takers"
          value={stats.totalTestTakers}
          color="#3B82F6"
          detail="Total unique"
        />
        <StatCard
          icon={TrendingUp}
          label="Sessions"
          value={stats.totalSessions}
          color="#8B5CF6"
          detail="Total completed"
        />
      </div>

      {/* Two Column Layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '2fr 1fr',
        gap: '16px',
        marginBottom: '24px'
      }}>
        {/* Quick Actions */}
        <div style={{
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h2 style={{
            fontSize: '18px',
            fontWeight: 'bold',
            color: colors.textPrimary,
            marginBottom: '16px'
          }}>
            Quick Actions
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px'
          }}>
            <QuickAction to="/admin/upload" icon={Upload} label="Upload Questions" color="#EAB308" />
            <QuickAction to="/admin/calibration" icon={Settings} label="Calibrate" color="#10B981" />
            <QuickAction to="/admin/sessions" icon={Activity} label="View Sessions" color="#3B82F6" />
          </div>
        </div>

        {/* Recent Activity */}
        <div style={{
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h2 style={{
            fontSize: '18px',
            fontWeight: 'bold',
            color: colors.textPrimary,
            marginBottom: '16px'
          }}>
            Recent Activity
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ textAlign: 'center', padding: '20px', color: colors.textMuted }}>
              No recent activity
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div style={{
        background: colors.cardBg,
        border: `1px solid ${colors.primary}`,
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: colors.primary
        }} />
        <div style={{ fontWeight: '600', color: colors.primary }}>
          System Status:
        </div>
        <div style={{ color: colors.primary }}>
          All services operational
        </div>
      </div>
    </div>
  );
};

export default Dashboard;