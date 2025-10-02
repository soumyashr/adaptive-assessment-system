import React from 'react';
import Sidebar from './components/Sidebar';

const AdminLayout = ({ children }) => {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
};

export default AdminLayout;