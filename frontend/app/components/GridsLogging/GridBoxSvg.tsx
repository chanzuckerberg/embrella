'use client';

import React from 'react';
import { ReactSVG } from 'react-svg';

interface GridBoxSVGProps {
  size?: number;
  onClick?: () => void;
  onGridClick?: (gridPosition: number) => void;
  isSelected?: boolean;
  disableGridClick?: boolean;
  gridBoxData?: any; // Add type based on your grid box data structure
}

export const GridBoxSVG: React.FC<GridBoxSVGProps> = ({
  size = 200,
  onClick,
  onGridClick,
  isSelected = false,
  disableGridClick = false,
  gridBoxData,
}) => {
  // Helper function to get grid status for a given position
  const getGridStatus = (position: number): 'filled' | 'empty' | 'unknown' => {
    // This would be based on your gridBoxData structure
    // For now, returning 'unknown' as placeholder
    return 'unknown';
  };

  // Get grid style based on status
  const getGridStyle = (position: number) => {
    const status = getGridStatus(position);
    const baseStyle = {
      cursor: disableGridClick ? 'default' : 'pointer',
      transition: 'all 0.2s ease-in-out',
    };

    switch (status) {
      case 'filled':
        return {
          ...baseStyle,
          opacity: 0.7,
          filter: 'brightness(0.8)',
          fill: '#4CAF50', // Green for filled grids
        };
      case 'empty':
        return {
          ...baseStyle,
          fill: '#E0E0E0', // Light gray for empty grids
        };
      default:
        return {
          ...baseStyle,
          fill: '#92D3D5', // Default grid box color
        };
    }
  };

  return (
    <div
      style={{
        cursor: onClick ? 'pointer' : 'default',
        transform: isSelected ? 'scale(1.05)' : 'scale(1)',
        transition: 'transform 0.2s ease-in-out',
        filter: isSelected ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))' : 'none',
        position: 'relative',
        width: size,
        height: size,
        overflow: 'visible',
        borderRadius: '8px',
      }}
      onClick={onClick}
    >
      <ReactSVG
        src="/next/GridBox.svg"
        beforeInjection={(svg) => {
          svg.setAttribute('width', '100%');
          svg.setAttribute('height', '100%');
          svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

          // Add click handlers to individual grid areas using data-position attributes
          const allPaths = svg.querySelectorAll('path');

          allPaths.forEach((path) => {
            const dataPosition = path.getAttribute('data-position');

            // Check if this is a grid area by looking for data-position attribute
            if (dataPosition) {
              const gridNumber = parseInt(dataPosition, 10);

              if (gridNumber >= 1 && gridNumber <= 4) { // Assuming 4 grids max
                const status = getGridStatus(gridNumber);
                const gridStyle = getGridStyle(gridNumber);
                
                // Apply visual styling based on grid status
                Object.assign(path.style, gridStyle);

                // Only add click handlers if grid clicking is not disabled
                if (!disableGridClick) {
                  path.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (onGridClick) {
                      onGridClick(gridNumber);
                    }
                  });
                }
             
              }
            }
          });
        }}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block',
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 1,
        }}
      />
    </div>
  );
};