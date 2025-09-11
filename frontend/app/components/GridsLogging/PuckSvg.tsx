'use client';

import React, { useState, useEffect } from 'react';
import { ReactSVG } from 'react-svg';
import { PucksList, PuckSlots } from '@app/common/types/gridLogging/puckList';

interface PuckSVGProps {
  puck: PucksList;
  slots?: PuckSlots[];
  size?: number;
  onClick?: () => void;
  onSlotClick?: (slotPosition: number) => void;
  isSelected?: boolean;
}

export const PuckSVG: React.FC<PuckSVGProps> = ({ 
  puck, 
  slots = [],
  size = 200, 
  onClick, 
  onSlotClick,
  isSelected = false 
}) => {
  const puckColor = puck.color.startsWith('#') ? puck.color : `#${puck.color}`;
  console.log(`${puck.name}: ${puckColor}`, 'puckColor from API');

  const [svgContent, setSvgContent] = useState<string>('');

  // Load SVG content dynamically for each puck instance
  useEffect(() => {
    const loadSVG = async () => {
      try {
        const response = await fetch('/next/puck.svg');
        if (response.ok) {
          const svgText = await response.text();
          setSvgContent(svgText);
        } else {
          console.error('Failed to load SVG:', response.status);
        }
      } catch (error) {
        console.error('Error loading SVG:', error);
      }
    };
    
    loadSVG();
  }, []);

  return (
    <div 
      style={{ 
        cursor: onClick ? 'pointer' : 'default',
        transform: isSelected ? 'scale(1.05)' : 'scale(1)',
        transition: 'transform 0.2s ease-in-out',
        filter: isSelected ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))' : 'none',
        position: 'relative',
        width: size,
        height: size
      }}
      onClick={onClick}
    >
      {svgContent ? (
        <ReactSVG
          src={`data:image/svg+xml;base64,${btoa(svgContent)}`}
          beforeInjection={(svg) => {
            try {
              // Method 1: Update CSS styles - Target ALL red color classes
              const styleElement = svg.querySelector('style');
              if (styleElement) {
                let styleText = styleElement.textContent || '';
                
                // Replace ALL red color classes with the API color
                const redColorClasses = [
                  '.cls-1', '.cls-4', '.cls-5', '.cls-6', '.cls-7', '.cls-8', '.cls-9', 
                  '.cls-10', '.cls-11', '.cls-12', '.cls-14', '.cls-15', '.cls-18', 
                  '.cls-19', '.cls-20', '.cls-21', '.cls-22', '.cls-23', '.cls-24'
                ];
                
                redColorClasses.forEach(className => {
                  const regex = new RegExp(`(${className}\\s*\\{[^}]*fill:\\s*)#[0-9a-fA-F]{6}`, 'g');
                  styleText = styleText.replace(regex, `$1${puckColor}`);
                  const regex3 = new RegExp(`(${className}\\s*\\{[^}]*fill:\\s*)#[0-9a-fA-F]{3}`, 'g');
                  styleText = styleText.replace(regex3, `$1${puckColor}`);
                });
                
                styleElement.textContent = styleText;
              }
              
              // Method 2: Force update ALL red color elements
              const redColorClasses = [
                '.cls-1', '.cls-4', '.cls-5', '.cls-6', '.cls-7', '.cls-8', '.cls-9', 
                '.cls-10', '.cls-11', '.cls-12', '.cls-14', '.cls-15', '.cls-18', 
                '.cls-19', '.cls-20', '.cls-21', '.cls-22', '.cls-23', '.cls-24'
              ];
              
              redColorClasses.forEach(className => {
                const elements = svg.querySelectorAll(className);
                elements.forEach(element => {
                  // Only update if it's not a text element
                  if (!element.tagName.toLowerCase().includes('text')) {
                    element.setAttribute('fill', puckColor);
                    element.style.fill = puckColor;
                  }
                });
              });
              
              // Method 3: Update gradients
              const gradients = svg.querySelectorAll('linearGradient, radialGradient');
              gradients.forEach(gradient => {
                const stops = gradient.querySelectorAll('stop');
                stops.forEach(stop => {
                  stop.setAttribute('stop-color', puckColor);
                });
              });
              
              console.log(`${puck.name}: Applied color ${puckColor} to ALL red elements`);
            } catch (error) {
              console.error('Error in color injection:', error);
            }
          }}
          afterInjection={(error, svg) => {
            if (error) {
              console.error('Error in afterInjection:', error);
              return;
            }
            
            try {
              if (svg) {
                // Make ALL circles use the API color (slots)
                const allCircles = svg.querySelectorAll('circle');
                allCircles.forEach((circle, index) => {
                  const r = parseFloat(circle.getAttribute('r') || '0');
                  
                  // Make all circles use the API color if they're in a reasonable size range
                  if (r > 3 && r < 25) {
                    circle.setAttribute('fill', puckColor);
                    circle.setAttribute('stroke', '#333333');
                    circle.setAttribute('stroke-width', '1.5');
                    circle.style.cursor = 'pointer';
                    circle.style.transition = 'all 0.2s ease';
                    
                    // Add hover effects
                    circle.addEventListener('mouseenter', () => {
                      circle.setAttribute('stroke', '#ffffff');
                      circle.setAttribute('stroke-width', '3');
                    });
                    
                    circle.addEventListener('mouseleave', () => {
                      circle.setAttribute('stroke', '#333333');
                      circle.setAttribute('stroke-width', '1.5');
                    });
                    
                    // Add click handler
                    circle.addEventListener('click', (e) => {
                      e.stopPropagation();
                      console.log(`Slot ${index + 1} clicked on puck ${puck.name}`);
                      onSlotClick?.(index + 1);
                    });
                  }
                });
                
                // Make ALL text elements white and bold
                const allTexts = svg.querySelectorAll('text');
                allTexts.forEach(text => {
                  text.setAttribute('fill', '#ffffff');
                  text.setAttribute('font-weight', 'bold');
                  text.setAttribute('font-size', '12');
                });
                
                // Make orientation markers white
                const allEllipses = svg.querySelectorAll('ellipse');
                allEllipses.forEach(ellipse => {
                  const rx = parseFloat(ellipse.getAttribute('rx') || '0');
                  const ry = parseFloat(ellipse.getAttribute('ry') || '0');
                  
                  // Small ellipses are likely orientation markers
                  if (rx < 10 && ry < 10) {
                    ellipse.setAttribute('fill', '#ffffff');
                    ellipse.setAttribute('stroke', '#333333');
                    ellipse.setAttribute('stroke-width', '1');
                  }
                });
                
                console.log(`${puck.name}: Applied API color to slots and white text`);
              }
            } catch (error) {
              console.error('Error in afterInjection processing:', error);
            }
          }}
          style={{ width: '100%', height: '100%' }}
        />
      ) : (
        <div style={{ 
          width: '100%', 
          height: '100%', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px'
        }}>
          Loading...
        </div>
      )}
      
      {/* Puck Label */}
      <div style={{ 
        textAlign: 'center', 
        marginTop: '8px',
        fontWeight: 'bold',
        color: isSelected ? '#1976d2' : '#333',
        fontSize: '14px'
      }}>
        {puck.name}
      </div>
    </div>
  );
};