import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// CRITICAL: Import CSS in correct order!
// 1. Index CSS FIRST (has CSS variables)
import './index.css';

// 2. Then NotificationProvider
import NotificationProvider from './providers/NotificationProvider';

// 3. Then Admin and Student components
import AdminApp from './admin/AdminApp';
import StudentApp from './student/App';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <NotificationProvider>
        <Routes>
          {/* Admin Routes */}
          <Route path="/admin/*" element={<AdminApp />} />

          {/* Student Routes */}
          <Route path="/student/*" element={<StudentApp />} />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/student" replace />} />
        </Routes>
      </NotificationProvider>
    </BrowserRouter>
  </React.StrictMode>
);