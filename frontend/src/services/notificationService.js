// frontend/src/services/notificationService.js
/**
 * Global Notification Service
 * Replace alert() with professional notifications throughout your app
 */

class NotificationService {
  constructor() {
    this.listeners = [];
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify(message, type = 'info', duration = 3000) {
    this.listeners.forEach(listener => {
      listener({ message, type, duration });
    });
  }

  success(message, duration = 3000) {
    this.notify(message, 'success', duration);
  }

  error(message, duration = 4000) {
    this.notify(message, 'error', duration);
  }

  warning(message, duration = 3500) {
    this.notify(message, 'warning', duration);
  }

  info(message, duration = 3000) {
    this.notify(message, 'info', duration);
  }
}

// Create singleton instance
const notificationService = new NotificationService();

export default notificationService;

// Usage examples:
// notificationService.success('User created successfully!');
// notificationService.error('Failed to save data');
// notificationService.warning('Session will expire soon');
// notificationService.info('New update available');