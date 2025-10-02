import React from 'react';
import Sidebar from './components/Sidebar';
import { theme } from '../config/theme';

const AdminLayout = ({ children }) => {
  return (
    <div className={`flex min-h-screen ${theme('bg-gray-900', 'bg-gray-50')}`}>
      <Sidebar />
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
};

export default AdminLayout;