// src/App.jsx - Sidebar Only
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './admin/components/Sidebar';
import Dashboard from './admin/pages/Dashboard';
import ItemBanksPage from './admin/pages/ItemBanksPage';
import Calibration from './admin/pages/Calibration';
import UploadData from './admin/pages/UploadData';
// import StudentPage from './student/StudentPage';
import { initializeTheme } from './config/theme';

function App() {
  // Initialize theme on app load
  React.useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <Router>
      <div className="app-container">
        <Routes>
          {/* Admin Routes with Sidebar */}
          <Route path="/admin/*" element={
            <div className="flex">
              {/* Sidebar on the left */}
              <Sidebar />

              {/* Main content area on the right */}
              <div className="flex-1">
                <Routes>
                  <Route index element={<Dashboard />} />
                  <Route path="item-banks" element={<ItemBanksPage />} />
                  <Route path="calibration" element={<Calibration />} />
                  <Route path="upload" element={<UploadData />} />
                </Routes>
              </div>
            </div>
          } />

          {/* Student Route - No Sidebar */}
          <Route path="/student" element={<StudentPage />} />

          {/* Default Route */}
          <Route path="/" element={
            <div className="flex">
              <Sidebar />
              <Dashboard />
            </div>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;