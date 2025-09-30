/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        'tier-c1': '#ef4444',
        'tier-c2': '#f97316', 
        'tier-c3': '#eab308',
        'tier-c4': '#22c55e'
      }
    },
  },
  plugins: [],
}