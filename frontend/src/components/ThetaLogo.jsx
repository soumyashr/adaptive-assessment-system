// src/components/ThetaLogo.jsx
import React from 'react';

const ThetaLogo = ({ className = "w-10 h-10", showBackground = true }) => {
  return (
    <svg
      className={className}
      viewBox="0 0 841.9 595.3"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Light background gradient - pure yellow to green */}
        <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor: '#FFFDE7', stopOpacity: 1}} />
          <stop offset="50%" style={{stopColor: '#F1F8E9', stopOpacity: 1}} />
          <stop offset="100%" style={{stopColor: '#E8F5E9', stopOpacity: 1}} />
        </linearGradient>

        {/* Much darker foreground gradient - deep yellow to dark green */}
        <linearGradient id="thetaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor: '#F57F17', stopOpacity: 1}} />
          <stop offset="50%" style={{stopColor: '#558B2F', stopOpacity: 1}} />
          <stop offset="100%" style={{stopColor: '#1B5E20', stopOpacity: 1}} />
        </linearGradient>

        {/* Glow effect */}
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* Light gradient background */}
      {showBackground && <rect width="841.9" height="595.3" fill="url(#bgGradient)"/>}

      {/* Mathematical Greek letter Theta (θ) - centered */}
      <g transform="translate(420.95, 297.65)" filter="url(#glow)">
        {/* Vertical elongated ellipse for theta body */}
        <ellipse
          cx="0"
          cy="0"
          rx="100"
          ry="180"
          fill="none"
          stroke="url(#thetaGradient)"
          strokeWidth="32"
        />

        {/* Horizontal line through the middle - made thicker and longer for visibility */}
        <line
          x1="-130"
          y1="0"
          x2="130"
          y2="0"
          stroke="url(#thetaGradient)"
          strokeWidth="40"
          strokeLinecap="round"
        />
      </g>
    </svg>
  );
};

export default ThetaLogo;