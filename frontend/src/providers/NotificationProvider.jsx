// frontend/src/providers/NotificationProvider.jsx
import React, { useEffect, useState } from 'react';
import { NotificationContainer } from '../components/Notification.jsx';
import notificationService from '../services/notificationService.js';


/**
 * Root-level Notification Provider
 * Wrap your entire app with this component
 */
const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    const unsubscribe = notificationService.subscribe((notification) => {
      const id = Date.now() + Math.random();
      setNotifications((prev) => [...prev, { id, ...notification }]);
    });

    return unsubscribe;
  }, []);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <>
      {children}
      <NotificationContainer
        notifications={notifications}
        removeNotification={removeNotification}
      />
    </>
  );
};

export default NotificationProvider;