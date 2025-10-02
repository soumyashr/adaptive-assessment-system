// src/config/theme.js
// Toggle dark mode by changing this single value

export const DARK_MODE = true;  // Dark mode
// export const DARK_MODE = false; // Light mode


// Helper function to get theme classes
export const theme = (darkClasses, lightClasses = '') => {
  return DARK_MODE ? darkClasses : lightClasses;
};