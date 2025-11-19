'use client';

import React from 'react';
import { ReactSVG } from 'react-svg';
import { PuckSlotsResponse } from '@app/common/types/gridLogging/entities/puckList';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/details/gridBoxDetails';

interface GridBoxSVGProps {
  size?: number;
  onClick?: () => void;
  onGridClick?: (gridPosition: number) => void;
  isSelected?: boolean;
  disableGridClick?: boolean;
  gridBoxData?: GridBoxDetailResponse;
  selectedGrid?: number | null;
  slotsData?: PuckSlotsResponse;
  selectedSlot?: number | null;
}

export const GridBoxSVG: React.FC<GridBoxSVGProps> = ({
  size = 200,
  onClick,
  onGridClick,
  isSelected = false,
  disableGridClick = false,
  gridBoxData,
  selectedGrid: _selectedGrid = null,
  slotsData,
  selectedSlot = null,
}) => {
  // Get grid status for a given position
  const getGridStatus = (position: number): 'occupied' | 'empty' | 'unknown' => {
    // First check if we have grid box data for the selected slot
    if (gridBoxData?.grid_box?.positions) {
      const gridPosition = gridBoxData.grid_box.positions.find((p) => p.q === position);
      return gridPosition ? (gridPosition.occupied ? 'occupied' : 'empty') : 'unknown';
    }

    // Fallback: check if the slot itself is filled (from slots data)
    if (slotsData && selectedSlot) {
      const slotData = slotsData.slots.find((slot) => slot.position === selectedSlot);
      return slotData?.status === 'filled' ? 'occupied' : 'empty';
    }

    return 'unknown';
  };

  // Get grid style based on status
  const getGridStyle = (position: number) => {
    const status = getGridStatus(position);
    const baseStyle = {
      cursor: disableGridClick ? 'default' : 'pointer',
      transition: 'all 0.2s ease-in-out',
    };

    if (status === 'occupied') {
      return {
        ...baseStyle,
        opacity: 0.3,
        fill: '#D3D3D3',
        strokeLinecap: 'round',
        strokeOpacity: '1',
        strokeWidth: '3px',
        filter: 'brightness(0.2)',
      };
    }

    return baseStyle;
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
              const maxGrids = gridBoxData?.grid_box?.max_grids || 4;

              if (gridNumber >= 1 && gridNumber <= maxGrids) {
                // 4 grids max
                const gridStyle = getGridStyle(gridNumber);

                // Apply visual styling based on grid status
                Object.assign(path.style, gridStyle);
              }
              // Only add click handlers if slot clicking is not disabled
              if (!disableGridClick) {
                path.addEventListener('click', (e) => {
                  e.stopPropagation();
                  if (onGridClick) {
                    onGridClick(gridNumber);
                  }
                });
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
