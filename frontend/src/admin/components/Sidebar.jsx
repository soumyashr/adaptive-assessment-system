import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { theme } from '../../config/theme';

const Sidebar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const menuItems = [
    { path: '/admin/dashboard', icon: '📊', label: 'Dashboard' },
    { path: '/admin/item-banks', icon: '🗂️', label: 'Item Banks' },
    { path: '/admin/upload', icon: '📤', label: 'Upload Data' },
    { path: '/admin/sessions', icon: '👥', label: 'Test Sessions' },
    { path: '/admin/calibration', icon: '⚙️', label: 'Calibration' },
  ];

  return (
    <div className={`w-64 ${theme('bg-gray-900 border-r border-gray-800', 'bg-white border-r border-gray-200')} ${theme('text-white', 'text-gray-900')} min-h-screen`}>
      {/* Logo */}
      <div className={`p-6 border-b ${theme('border-gray-800', 'border-gray-200')}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-xl font-bold text-white">θ</span>
          </div>
          <div>
            <h1 className={`text-lg font-bold ${theme('text-white', 'text-gray-900')}`}>MyTheta</h1>
            <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')}`}>Admin Panel</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition ${
              isActive(item.path)
                ? 'bg-blue-600 text-white'
                : theme('text-gray-300 hover:bg-gray-800', 'text-gray-700 hover:bg-gray-100')
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span className="font-medium">{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Bottom */}
      <div className={`absolute bottom-0 w-64 p-4 border-t ${theme('border-gray-800', 'border-gray-200')}`}>
        <div className="flex items-center gap-3 px-4 py-3">
          <div className={`w-8 h-8 ${theme('bg-gray-700', 'bg-gray-200')} rounded-full flex items-center justify-center`}>
            <span className="text-sm">👤</span>
          </div>
          <div>
            <div className={`text-sm font-medium ${theme('text-white', 'text-gray-900')}`}>Admin User</div>
            <div className={`text-xs ${theme('text-gray-400', 'text-gray-500')}`}>Administrator</div>
          </div>
        </div>
        <Link
          to="/student"
          className={`block text-center text-sm ${theme('text-gray-400 hover:text-white', 'text-gray-600 hover:text-gray-900')} mt-2 transition`}
        >
          Switch to Student View →
        </Link>
      </div>
    </div>
  );
};

export default Sidebar;