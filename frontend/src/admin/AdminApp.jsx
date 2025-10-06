import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout from './AdminLayout';

// Pages
import Dashboard from './pages/Dashboard';
import ItemBanksPage from './pages/ItemBanksPage';
import UploadData from './pages/UploadData';
import TestSessions from './pages/TestSessions';
import Calibration from './pages/Calibration';
import SessionDetail from './pages/SessionDetail';

const AdminApp = () => {
  return (
    <AdminLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/item-banks" element={<ItemBanksPage />} />
        <Route path="/upload" element={<UploadData />} />
        <Route path="/sessions" element={<TestSessions />} />
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
        <Route path="/calibration" element={<Calibration />} />
      </Routes>
    </AdminLayout>
  );
};

export default AdminApp;