'use client';

import React, { useId, useState } from 'react';
import { Tooltip } from '@mui/material';
import { PuckSlotsResponse, GridBoxDetailResponse } from '@app/common/types/gridLogging';
import {
  HOVER_LINE_WIDTH,
  LABEL_COLOR,
  LABEL_OUTLINE,
  LINE_WIDTH,
  RING_WIDTH,
  SELECTED_FILL,
  SELECTED_FILTER,
  slotPaint,
  SlotPaint,
  slotPalette,
} from '../slotPalette';
import { boxCells, GridBoxNumbering, Point, slotCenter, slotHitArea, slotLabel } from './gridBoxLayout';

export type GridBoxSize = 4 | 8;

// Padded leaves room around the ring for the selected scale/shadow; Tight crops to the ring so edges align with fields.
export enum GridBoxFit {
  Padded = 'padded',
  Tight = 'tight',
}

interface GridBoxSVGProps {
  size?: number;
  onClick?: () => void;
  onGridClick?: (gridPosition: number) => void;
  isSelected?: boolean;
  disableGridClick?: boolean;
  gridBoxData?: GridBoxDetailResponse;
  selectedGrid?: number | null;
  selectedGrids?: number[]; // multi-select; highlighted like selectedGrid
  slotsData?: PuckSlotsResponse;
  selectedSlot?: number | null;
  maxGrids?: GridBoxSize;
  numbering?: string;
  // Box color as hex (e.g. "fdb000"); falls back to the box's stored color.
  color?: string;
  fit?: GridBoxFit;
}

enum GridStatus {
  Occupied = 'occupied',
  Empty = 'empty',
  Unknown = 'unknown',
}

const DEFAULT_COLOR = '92D3D5';

// Drawing units: the box is drawn in a 200×200 viewBox, then scaled to `size`.
const VIEW = 200;
const CENTER: Point = { x: VIEW / 2, y: VIEW / 2 };
const BODY_RADIUS = 90;

// U-shaped notch at 12 o'clock, as cut into the real boxes.
const NOTCH_WIDTH = 34;
const NOTCH_DEPTH = 26;

// Threaded center hole: dashed inner ring hints at the thread.
const HOLE_STROKE = 2.5;
const THREAD_RADIUS = 0.62;
const THREAD_WIDTH = 1.5;
const THREAD_DASH = '3 2.2';
const THREAD_OPACITY = 0.8;

// Same oval, label and hole size for every box size.
const SLOT = { rx: 25, ry: 14, font: 15 };
const HOLE_RADIUS = 11;

/**
 * Slot placement per box size. Columns sit close to the center hole to keep a margin from the ring,
 * and 8-box columns bow outward to follow the rim like the machined slots.
 */
const SLOT_LAYOUT: Record<GridBoxSize, { gap: Point; bow: number }> = {
  4: { gap: { x: 40, y: 40 }, bow: 0 },
  8: { gap: { x: 33, y: 34 }, bow: 9 },
};

/**
 * Body outline: a circle with a U-notch cut down from 12 o'clock.
 *
 *        ┌┐  ← notch walls drop NOTCH_DEPTH, rounded bottom
 *     ╭──┘└──╮
 *     │      │
 *     ╰──────╯
 */
const bodyPath = () => {
  const half = NOTCH_WIDTH / 2;
  const rimY = CENTER.y - Math.sqrt(BODY_RADIUS * BODY_RADIUS - half * half);
  const wallBottom = CENTER.y - BODY_RADIUS + NOTCH_DEPTH - half;

  return [
    `M ${CENTER.x + half} ${rimY}`,
    `A ${BODY_RADIUS} ${BODY_RADIUS} 0 1 1 ${CENTER.x - half} ${rimY}`,
    `L ${CENTER.x - half} ${wallBottom}`,
    `A ${half} ${half} 0 0 0 ${CENTER.x + half} ${wallBottom}`,
    'Z',
  ].join(' ');
};

const BODY_PATH = bodyPath();

// Tight viewBox: the ring's outer edge, e.g. "7 7 186 186".
const OUTER_RADIUS = BODY_RADIUS + RING_WIDTH / 2;
const VIEW_BOX: Record<GridBoxFit, string> = {
  [GridBoxFit.Padded]: `0 0 ${VIEW} ${VIEW}`,
  [GridBoxFit.Tight]: `${CENTER.x - OUTER_RADIUS} ${CENTER.y - OUTER_RADIUS} ${OUTER_RADIUS * 2} ${OUTER_RADIUS * 2}`,
};

export const GridBoxSVG: React.FC<GridBoxSVGProps> = ({
  size = 200,
  onClick,
  onGridClick,
  isSelected = false,
  disableGridClick = false,
  gridBoxData,
  selectedGrid = null,
  selectedGrids,
  slotsData,
  selectedSlot = null,
  maxGrids = 4,
  numbering = GridBoxNumbering.Ucw,
  color,
  fit = GridBoxFit.Padded,
}) => {
  const palette = slotPalette(color ?? gridBoxData?.grid_box?.color ?? DEFAULT_COLOR);

  // Get grid status for a given position
  const getGridStatus = (position: number): GridStatus => {
    // First check if we have grid box data for the selected slot
    if (gridBoxData?.grid_box?.positions) {
      const gridPosition = gridBoxData.grid_box.positions.find((p) => p.q === position);
      if (!gridPosition) return GridStatus.Unknown;
      return gridPosition.occupied ? GridStatus.Occupied : GridStatus.Empty;
    }

    // Fallback: check if the slot itself is filled (from slots data)
    if (slotsData && selectedSlot) {
      const slotData = slotsData.slots.find((slot) => slot.position === selectedSlot);
      return slotData?.status === 'filled' ? GridStatus.Occupied : GridStatus.Empty;
    }

    return GridStatus.Unknown;
  };

  // Slot under the pointer, outlined bolder.
  const [hovered, setHovered] = useState<number | null>(null);

  // Highlighted slot wins.
  const slotStyle = (position: number) => {
    const isOccupied = getGridStatus(position) === GridStatus.Occupied;

    if (position === selectedGrid || selectedGrids?.includes(position))
      return { paint: { fill: SELECTED_FILL } as SlotPaint, filter: SELECTED_FILTER, isSelected: true };

    return { paint: slotPaint(palette, isOccupied), filter: undefined, isSelected: false };
  };

  // Hover text: "Position 2 · Grid XYZ · clipped" or "Position 2 · Free"; none without box data.
  const slotTitle = (position: number) => {
    const slot = gridBoxData?.grid_box?.positions.find((p) => p.q === position);
    if (!slot) return '';

    if (!slot.occupied) return `Position ${position} · Free`;

    const clipped = slot.clipped ? ' · clipped' : '';

    return `Position ${position} · ${slot.grid_name ?? 'Filled'}${clipped}`;
  };

  const layout = SLOT_LAYOUT[maxGrids] ?? SLOT_LAYOUT[4];

  // Body-shaped clip so hit areas stop at the rim; unique per instance.
  const clipId = useId();

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
      <svg viewBox={VIEW_BOX[fit]} width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        <defs>
          <clipPath id={clipId}>
            <path d={BODY_PATH} />
          </clipPath>
        </defs>

        <path d={BODY_PATH} fill={palette.body} stroke={palette.ring} strokeWidth={RING_WIDTH} strokeLinejoin="round" />

        {/* Threaded center hole. */}
        <circle
          cx={CENTER.x}
          cy={CENTER.y}
          r={HOLE_RADIUS}
          fill={palette.bore}
          stroke={palette.ring}
          strokeWidth={HOLE_STROKE}
        />
        <circle
          cx={CENTER.x}
          cy={CENTER.y}
          r={HOLE_RADIUS * THREAD_RADIUS}
          fill="none"
          stroke={palette.slot}
          strokeWidth={THREAD_WIDTH}
          strokeDasharray={THREAD_DASH}
          opacity={THREAD_OPACITY}
        />

        {/* One oval per slot, placed by column/row and labelled by numbering. */}
        {boxCells(maxGrids).map((cell) => {
          const position = slotLabel(cell, maxGrids, numbering);
          const { x, y } = slotCenter(cell, maxGrids, CENTER, layout.gap, layout.bow);
          const { paint, filter, isSelected: isPicked } = slotStyle(position);
          const isHovered = hovered === position;
          const hit = slotHitArea(cell, maxGrids, CENTER, layout.gap, BODY_RADIUS);

          const handleClick = (e: React.MouseEvent) => {
            e.stopPropagation();
            onGridClick?.(position);
          };

          return (
            // Non-interactive: the pointer passes through to the slot above.
            <Tooltip key={position} title={slotTitle(position)} arrow placement="top" disableInteractive>
              <g
                data-position={position}
                onClick={disableGridClick ? undefined : handleClick}
                onMouseEnter={disableGridClick ? undefined : () => setHovered(position)}
                onMouseLeave={disableGridClick ? undefined : () => setHovered(null)}
                style={{
                  cursor: disableGridClick ? 'default' : 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  filter,
                }}
              >
                {/* Invisible click area: the slot's whole cell, not just the oval. */}
                {!disableGridClick && <rect {...hit} fill="transparent" clipPath={`url(#${clipId})`} />}
                <ellipse
                  cx={x}
                  cy={y}
                  rx={SLOT.rx}
                  ry={SLOT.ry}
                  fill={paint.fill}
                  stroke={isPicked ? palette.label : palette.line}
                  strokeWidth={isHovered || isPicked ? HOVER_LINE_WIDTH : LINE_WIDTH}
                  strokeDasharray={paint.dash}
                />
                <text
                  x={x}
                  y={y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontFamily="sans-serif"
                  fontWeight={700}
                  fontSize={SLOT.font}
                  fill={LABEL_COLOR}
                  stroke={palette.label}
                  strokeWidth={SLOT.font * LABEL_OUTLINE}
                  strokeLinejoin="round"
                  paintOrder="stroke"
                >
                  {position}
                </text>
              </g>
            </Tooltip>
          );
        })}
      </svg>
    </div>
  );
};
