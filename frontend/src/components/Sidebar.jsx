// ============================================
// 1. src/admin/components/Sidebar.jsx
// ============================================
import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { getThemeColors, DARK_MODE, toggleDarkMode } from '../config/theme';
import { BarChart3, Database, Upload, Settings, Activity } from 'lucide-react';

const Sidebar = () => {
  const [isDark, setIsDark] = useState(DARK_MODE);
  const colors = getThemeColors();

  const handleToggleTheme = () => {
    const newTheme = toggleDarkMode();
    setIsDark(newTheme);
    window.location.reload();
  };

  const navItems = [
    { name: 'Dashboard', path: '/admin', icon: BarChart3 },
    { name: 'Item Banks', path: '/admin/item-banks', icon: Database },
    { name: 'Upload Data', path: '/admin/upload', icon: Upload },
    { name: 'Calibration', path: '/admin/calibration', icon: Settings },
    { name: 'Sessions', path: '/admin/sessions', icon: Activity }
  ];

  return (
    <div style={{
      width: '260px',
      minHeight: '100vh',
      background: DARK_MODE ? '#1f1f1f' : '#ffffff',
      borderRight: `1px solid ${colors.cardBorder}`,
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh'
    }}>
      {/* Logo */}
      <div style={{
        padding: '24px',
        borderBottom: `1px solid ${colors.cardBorder}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: colors.primaryGradient,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            color: 'white'
          }}>
            ✨
          </div>
          <div>
            <h1 style={{
              fontSize: '16px',
              fontWeight: 'bold',
              color: DARK_MODE ? '#ffffff' : '#1a1a1a',
              margin: 0
            }}>
              Admin Panel
            </h1>
            <p style={{
              fontSize: '12px',
              color: DARK_MODE ? '#9ca3af' : '#6b7280',
              margin: 0
            }}>
              Adaptive Testing
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '16px' }}>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {navItems.map((item) => (
            <li key={item.path} style={{ marginBottom: '4px' }}>
              <NavLink
                to={item.path}
                end={item.path === '/admin'}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  background: isActive ? colors.primaryGradient : 'transparent',
                  color: isActive ? 'white' : (DARK_MODE ? '#e5e7eb' : '#374151'),
                  fontWeight: isActive ? '600' : '500',
                  transition: 'all 0.2s'
                })}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.classList.contains('active')) {
                    e.currentTarget.style.background = DARK_MODE ? 'rgba(255,255,255,0.08)' : '#f3f4f6';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.classList.contains('active')) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <item.icon size={20} />
                <span>{item.name}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Theme Toggle */}
      <div style={{
        padding: '16px',
        borderTop: `1px solid ${colors.cardBorder}`
      }}>
        <button
          onClick={handleToggleTheme}
          style={{
            width: '100%',
            padding: '12px 16px',
            borderRadius: '8px',
            border: `2px solid ${colors.primary}`,
            background: DARK_MODE ? 'rgba(16, 185, 129, 0.15)' : '#fef3c7',
            color: DARK_MODE ? '#ffffff' : colors.textPrimary,
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '14px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.02)';
            e.currentTarget.style.boxShadow = '0 4px 8px rgba(16, 185, 129, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isDark ? '☀️' : '🌙'}
            <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
          </div>
          →
        </button>
      </div>

      {/* User Profile */}
      <div style={{
        padding: '16px',
        borderTop: `1px solid ${colors.cardBorder}`,
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          background: colors.primaryGradient,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold'
        }}>
          A
        </div>
        <div style={{ flex: 1 }}>
          <p style={{
            fontSize: '14px',
            fontWeight: '600',
            color: DARK_MODE ? '#ffffff' : '#1a1a1a',
            margin: 0
          }}>
            Admin User
          </p>
          <p style={{
            fontSize: '12px',
            color: DARK_MODE ? '#9ca3af' : '#6b7280',
            margin: 0
          }}>
            admin@test.com
          </p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;