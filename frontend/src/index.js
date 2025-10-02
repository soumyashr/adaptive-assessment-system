import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

// Admin interface
import AdminApp from './admin/AdminApp';

// Student interface
import StudentApp from './student/App';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Admin Routes */}
        <Route path="/admin/*" element={<AdminApp />} />

        {/* Student Routes */}
        <Route path="/student/*" element={<StudentApp />} />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/student" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);