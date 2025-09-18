'use client';

import React from 'react';
import { ReactSVG } from 'react-svg';
import { PucksList, PuckSlots } from '@app/common/types/gridLogging/puckList';

interface PuckSVGProps {
  puck: PucksList;
  slots?: PuckSlots[];
  size?: number;
  onClick?: () => void;
  onSlotClick?: (slotPosition: number) => void;
  isSelected?: boolean;
  disableSlotClick?: boolean;
}

export const PuckSVG: React.FC<PuckSVGProps> = ({
  puck,
  slots = [],
  size = 200,
  onClick,
  onSlotClick,
  isSelected = false,
  disableSlotClick = false,
}) => {
  const puckColor = puck.color.startsWith('#') ? puck.color : `#${puck.color}`;

  // Helper function to darken colors for borders
  const darkenColor = (color: string, amount: number): string => {
    const hex = color.replace('#', '');
    const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) - amount));
    const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) - amount));
    const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) - amount));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  };

  // Function to replace colors in the SVG with the API color
  const replaceColors = (svg: SVGElement, puckColor: string) => {
    const elements = svg.querySelectorAll('*');
    elements.forEach((element, index) => {
      const fill = element.getAttribute('fill');
      const stroke = element.getAttribute('stroke');

      // Replace specific colors with API color
      if (fill && isReplaceableColor(fill)) {
        if (isCircleElement(index)) {
          element.setAttribute('fill', puckColor);
        } else if (isMainPuckOutline(fill)) {
          element.setAttribute('fill', darkenColor(puckColor, 30));
        } else {
          element.setAttribute('fill', puckColor);
        }
      }
      if (stroke && isReplaceableColor(stroke)) {
        element.setAttribute('stroke', darkenColor(puckColor, 30));
      }
    });
  };

  const isReplaceableColor = (color: string): boolean => {
    const replaceableColors = [
      '#595959', // Individual circles/slots
      '#363636', // Circle borders AND some circles
      '#717171', // Main puck outline
      '#383838', // Details
      '#373737', // Other details
      '#393939',
      '#707070',
      '#383838',
      '#000000',
      '#3b3b3b',
    ];
    return replaceableColors.some((replaceable) => color.includes(replaceable));
  };

  const isCircleElement = (index: number): boolean => {
    return index >= 5 && index <= 16;
  };

  const isMainPuckOutline = (color: string): boolean => {
    return color.includes('#717171');
  };

  // Get slot status for a given position
  const getSlotStatus = (position: number): 'filled' | 'empty' | 'unknown' => {
    const slot = slots.find(s => s.position === position);
    return slot ? slot.status as 'filled' | 'empty' : 'unknown';
  };

  // Get slot style based on status
  const getSlotStyle = (position: number) => {
    const status = getSlotStatus(position);
    const baseStyle = {
      cursor: disableSlotClick ? 'default' : 'pointer',
      transition: 'all 0.2s ease-in-out',
    };

    switch (status) {
      case 'filled':
        return {
          ...baseStyle,
          opacity: 0.7,
          filter: 'brightness(0.8)',
          fill: 'grey',
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
      {/* SVG Background */}
      <ReactSVG
        src="/next/puck.svg"
        beforeInjection={(svg) => {
          svg.setAttribute('width', '100%');
          svg.setAttribute('height', '100%');
          svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

          // Add click handlers to individual slot circles using data-position attributes
          const allPaths = svg.querySelectorAll('path');

          allPaths.forEach((circle) => {
            const dataPosition = circle.getAttribute('data-position');

            // Check if this is a slot circle by looking for data-position attribute and specific fill color
            if (dataPosition) {
              const slotNumber = parseInt(dataPosition, 10);

              if (slotNumber >= 1 && slotNumber <= 12) {
                const status = getSlotStatus(slotNumber);
                const slotStyle = getSlotStyle(slotNumber);
                
                // Apply visual styling based on slot status
                Object.assign(circle.style, slotStyle);

                // Only add click handlers if slot clicking is not disabled
                if (!disableSlotClick) {
                  circle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (onSlotClick) {
                      onSlotClick(slotNumber);
                    }
                  });
                }
              }
            }
          });

          // Replace colors with API color
          replaceColors(svg, puckColor);
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