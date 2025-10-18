// ============================================
// 2. src/admin/AdminLayout.jsx
// ============================================
import React from 'react';
import Sidebar from '../components/Sidebar';
import { getBackgroundGradient } from '../config/theme';

const AdminLayout = ({ children }) => {
  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: getBackgroundGradient()
    }}>
      <Sidebar />
      <div style={{
        flex: 1,
        overflowY: 'auto',
        maxHeight: '100vh'
      }}>
        {children}
      </div>
    </div>
  );
};

export default AdminLayout;