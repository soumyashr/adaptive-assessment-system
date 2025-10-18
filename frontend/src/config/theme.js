// src/config/theme.js - Updated with Standard Gradient Background

// Check localStorage for saved theme preference, default to false (light mode)
let isDarkMode = localStorage.getItem('darkMode') === 'true';
// let isDarkMode = localStorage.getItem('darkMode') === 'false';

// Export as a mutable variable
export let DARK_MODE = isDarkMode;

// Function to toggle dark mode
export const toggleDarkMode = () => {
  DARK_MODE = !DARK_MODE;
  localStorage.setItem('darkMode', DARK_MODE.toString());
  // Trigger a custom event to notify all components
  window.dispatchEvent(new Event('themeChange'));
  return DARK_MODE;
};

// STANDARD GRADIENT BACKGROUNDS - Use across ALL pages
export const getBackgroundGradient = () => {
  if (DARK_MODE) {
    return 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)';
  } else {
    // Beautiful yellow-green gradient matching the reference image
    return 'linear-gradient(135deg, #fef3c7 0%, #fef9c3 10%, #fef08a 20%, #e0f2fe 40%, #bae6fd 60%, #7dd3fc 80%, #38bdf8 100%)';
  }
};

// Enhanced color palette
export const getThemeColors = () => {
  if (DARK_MODE) {
    return {
      // Backgrounds
      bgPrimary: '#1a1a1a',
      bgSecondary: '#2a2a2a',
      bgTertiary: '#3a3a3a',

      // Card backgrounds
      cardBg: '#2a2a2a',
      cardBgHover: '#323232',
      cardBorder: '#404040',

      // Text colors
      textPrimary: '#ffffff',
      textSecondary: '#e5e5e5',
      textMuted: '#a0a0a0',
      textDisabled: '#666666',

      // Input fields
      inputBg: '#3a3a3a',
      inputBorder: '#505050',
      inputBorderFocus: '#10B981',
      inputText: '#ffffff',
      inputPlaceholder: '#888888',

      // Buttons - Keep brand gradient for consistency
      primaryGradient: 'linear-gradient(90deg, #EAB308 0%, #84CC16 25%, #22C55E 50%, #10B981 75%, #14B8A6 100%)',
      primaryGradientHover: 'linear-gradient(90deg, #CA8A04 0%, #65A30D 25%, #16A34A 50%, #059669 75%, #0D9488 100%)',

      // Status colors
      success: '#22C55E',
      successBg: 'rgba(34, 197, 94, 0.1)',
      warning: '#EAB308',
      warningBg: 'rgba(234, 179, 8, 0.1)',
      error: '#EF4444',
      errorBg: 'rgba(239, 68, 68, 0.1)',
      info: '#3B82F6',
      infoBg: 'rgba(59, 130, 246, 0.1)',

      // Semantic colors
      primary: '#10B981',
      secondary: '#EAB308',

      // Shadows
      shadowSm: '0 1px 3px 0 rgba(0, 0, 0, 0.5)',
      shadowMd: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
      shadowLg: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',

      // Modal overlay
      modalOverlay: 'rgba(0, 0, 0, 0.85)',
    };
  } else {
    return {
      // Backgrounds - Use gradient background via getBackgroundGradient()
      bgPrimary: '#fef3c7',
      bgSecondary: '#fef9c3',
      bgTertiary: '#fef08a',

      // Card backgrounds
      cardBg: '#ffffff',
      cardBgHover: '#fafafa',
      cardBorder: '#e7e5e4',

      // Text colors
      textPrimary: '#1a1a1a',
      textSecondary: '#2d2d2d',
      textMuted: '#737373',
      textDisabled: '#a3a3a3',

      // Input fields
      inputBg: '#fef9c3',
      inputBorder: '#d1d5db',
      inputBorderFocus: '#10B981',
      inputText: '#1a1a1a',
      inputPlaceholder: '#9ca3af',

      // Buttons - Brand gradient
      primaryGradient: 'linear-gradient(90deg, #EAB308 0%, #84CC16 25%, #22C55E 50%, #10B981 75%, #14B8A6 100%)',
      primaryGradientHover: 'linear-gradient(90deg, #CA8A04 0%, #65A30D 25%, #16A34A 50%, #059669 75%, #0D9488 100%)',

      // Status colors
      success: '#16A34A',
      successBg: '#dcfce7',
      warning: '#CA8A04',
      warningBg: '#fef9c3',
      error: '#DC2626',
      errorBg: '#fee2e2',
      info: '#2563EB',
      infoBg: '#dbeafe',

      // Semantic colors
      primary: '#10B981',
      secondary: '#EAB308',

      // Shadows
      shadowSm: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      shadowMd: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      shadowLg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',

      // Modal overlay
      modalOverlay: 'rgba(0, 0, 0, 0.75)',
    };
  }
};

// Helper function for conditional classes (kept for backward compatibility)
export const theme = (darkClass, lightClass) => {
  return DARK_MODE ? darkClass : lightClass;
};

// Get current theme name
export const getThemeName = () => DARK_MODE ? 'dark' : 'light';

// Initialize theme on app load
export const initializeTheme = () => {
  DARK_MODE = localStorage.getItem('darkMode') === 'true';
  return DARK_MODE;
};