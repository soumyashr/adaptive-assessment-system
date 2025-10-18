// src/components/ReactLogo.jsx
import React from 'react';

const ReactLogo = ({ className = "w-10 h-10", showBackground = true }) => {
  return (
    <svg
      className={className}
      viewBox="0 0 841.9 595.3"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Light background gradient - pure yellow to green */}
        <linearGradient id="bgGradientReact" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor: '#FFFDE7', stopOpacity: 1}} />
          <stop offset="50%" style={{stopColor: '#F1F8E9', stopOpacity: 1}} />
          <stop offset="100%" style={{stopColor: '#E8F5E9', stopOpacity: 1}} />
        </linearGradient>

        {/* Much darker foreground gradient - deep yellow to dark green */}
        <linearGradient id="reactGradientColor" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor: '#F57F17', stopOpacity: 1}} />
          <stop offset="50%" style={{stopColor: '#558B2F', stopOpacity: 1}} />
          <stop offset="100%" style={{stopColor: '#1B5E20', stopOpacity: 1}} />
        </linearGradient>

        {/* Glow effect */}
        <filter id="glowReact">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* Light gradient background */}
      {showBackground && <rect width="841.9" height="595.3" fill="url(#bgGradientReact)"/>}

      {/* React Atom Structure - centered at 420.95, 297.65 */}
      <g transform="translate(420.95, 297.65)" filter="url(#glowReact)">
        {/* Ellipse 1 */}
        <ellipse
          cx="0"
          cy="0"
          rx="200"
          ry="70"
          fill="none"
          stroke="url(#reactGradientColor)"
          strokeWidth="18"
        />

        {/* Ellipse 2 (rotated 60 degrees) */}
        <ellipse
          cx="0"
          cy="0"
          rx="200"
          ry="70"
          fill="none"
          stroke="url(#reactGradientColor)"
          strokeWidth="18"
          transform="rotate(60)"
        />

        {/* Ellipse 3 (rotated 120 degrees) */}
        <ellipse
          cx="0"
          cy="0"
          rx="200"
          ry="70"
          fill="none"
          stroke="url(#reactGradientColor)"
          strokeWidth="18"
          transform="rotate(120)"
        />

        {/* Center dot */}
        <circle cx="0" cy="0" r="25" fill="url(#reactGradientColor)"/>
      </g>
    </svg>
  );
};

export default ReactLogo;