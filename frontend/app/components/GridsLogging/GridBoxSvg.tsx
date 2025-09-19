'use client';

import React from 'react';
import { ReactSVG } from 'react-svg';

interface GridBoxSVGProps {
  size?: number;
  onClick?: () => void;
  onGridClick?: (gridPosition: number) => void;
  isSelected?: boolean;
  disableGridClick?: boolean;
  gridBoxData?: any;
  selectedGrid?: number | null;
  isOccupied?: boolean;
}

export const GridBoxSVG: React.FC<GridBoxSVGProps> = ({
  size = 200,
  onClick,
  onGridClick,
  isSelected = false,
  disableGridClick = false,
  gridBoxData,
  selectedGrid = null,
  isOccupied = false,
}) => {
  // Get grid status for a given position (following the same pattern as PuckSVG)
  const getGridStatus = (position: number): 'occupied' | 'empty' | 'unknown' => {
    if (!gridBoxData?.grid_box?.positions) return 'unknown';
    const gridPosition = gridBoxData.grid_box.positions.find((p: any) => p.q === position);
    return gridPosition ? (gridPosition.occupied ? 'occupied' : 'empty') : 'unknown';
  };

  // Get grid style based on status (following the EXACT same pattern as PuckSVG)
  const getGridStyle = (position: number) => {
    const status = getGridStatus(position);
    const baseStyle = {
      cursor: disableGridClick ? 'default' : 'pointer',
      transition: 'all 0.2s ease-in-out',
    };

    switch (status) {
      case 'occupied':
        return {
          ...baseStyle,
          opacity: 0.1,        
          filter: 'brightness(0.4)', 
        };
      default:
        return baseStyle;     
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

              if (gridNumber >= 1 && gridNumber <= 4) { // 4 grids max
                const status = getGridStatus(gridNumber);
                const gridStyle = getGridStyle(gridNumber);
                
                // Apply visual styling based on grid status (EXACT same pattern as PuckSVG)
                Object.assign(path.style, gridStyle);
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