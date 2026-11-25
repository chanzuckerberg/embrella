'use client';

import React, { useState } from 'react';
import { Tooltip } from '@mui/material';
import { PuckList, PuckSlots } from '@app/common/types/gridLogging';
import {
  HOVER_LINE_WIDTH,
  LABEL_COLOR,
  LABEL_OUTLINE,
  LINE_WIDTH,
  RING_WIDTH,
  SELECTED_FILL,
  selectedFilter,
  slotPaint,
  SlotPaint,
  slotPalette,
} from '../slotPalette';
import { OUTLINE_CENTER, OUTLINE_EXTENT, OUTLINE_PATH, OUTLINE_PIVOT, SLOT_CENTERS, SLOT_RADIUS } from './puckArt';

interface PuckSVGProps {
  puck: PuckList;
  slots?: PuckSlots[];
  size?: number;
  onClick?: () => void;
  onSlotClick?: (slotPosition: number) => void;
  isSelected?: boolean;
  disableSlotClick?: boolean;
  highlightedSlot?: number;
  mode?: SlotMode;
  onSlotHover?: (slotPosition: number | null) => void;
}

/**
 * View: filled slots clickable, hover tooltip names the occupant.
 * Pick: filled slots blocked, no tooltip; the caller shows hover text via onSlotHover.
 */
export enum SlotMode {
  View = 'view',
  Pick = 'pick',
}

const FILLED = 'filled';

// "Slot 4 · DD-004" or "Slot 4 · Free".
export const describeSlot = (slots: PuckSlots[], position: number) => {
  const slot = slots.find((s) => s.position === position);
  const occupant = slot?.status === FILLED ? (slot.grid_box_name ?? 'Filled') : 'Free';

  return `Slot ${position} · ${occupant}`;
};

// Outline is enlarged around the slots, so the rim clears them.
const OUTLINE_SCALE = 1.08;

/**
 * ViewBox fits the enlarged outline. Scaling around the pivot moves the outline center:
 *   center' = pivot + scale × (center − pivot)
 */
const VIEW = OUTLINE_EXTENT * OUTLINE_SCALE;
const VIEW_ORIGIN = {
  x: OUTLINE_PIVOT.x + OUTLINE_SCALE * (OUTLINE_CENTER.x - OUTLINE_PIVOT.x) - VIEW / 2,
  y: OUTLINE_PIVOT.y + OUTLINE_SCALE * (OUTLINE_CENTER.y - OUTLINE_PIVOT.y) - VIEW / 2,
};

const OUTLINE_TRANSFORM = [
  `translate(${OUTLINE_PIVOT.x} ${OUTLINE_PIVOT.y})`,
  `scale(${OUTLINE_SCALE})`,
  `translate(${-OUTLINE_PIVOT.x} ${-OUTLINE_PIVOT.y})`,
].join(' ');

// Shared sizes are in 200-unit drawings; scale them to this viewBox.
const UNIT = VIEW / 200;

// Label size, like the grid box's.
const FONT = 14 * UNIT;

// Highlight glow sized like the grid box's.
const SELECTED_GLOW_FILTER = selectedFilter(UNIT);

// Invisible click target per slot: just under half the gap to its nearest neighbor.
const HIT_RADIUS = 88;

export const PuckSVG: React.FC<PuckSVGProps> = ({
  puck,
  slots,
  size = 200,
  onClick,
  onSlotClick,
  isSelected = false,
  disableSlotClick = false,
  highlightedSlot,
  mode = SlotMode.View,
  onSlotHover,
}) => {
  const palette = slotPalette(puck.color);

  // Slot under the pointer, outlined bolder.
  const [hovered, setHovered] = useState<number | null>(null);

  const hover = (position: number | null) => {
    setHovered(position);
    onSlotHover?.(position);
  };

  const isFilled = (position: number) => !!slots?.some((s) => s.position === position && s.status === FILLED);

  // No slot data (e.g. puck list): body-colored, so slots don't read as empty.
  const paint = (filled: boolean): SlotPaint => {
    if (!slots) return { fill: palette.body };

    return slotPaint(palette, filled, UNIT);
  };

  // Tooltip in view mode only; none without slot data.
  const slotTitle = (position: number) => (slots && mode === SlotMode.View ? describeSlot(slots, position) : '');

  // Highlighted slot wins.
  const slotStyle = (position: number) => {
    const filled = isFilled(position);

    if (position === highlightedSlot)
      return { paint: { fill: SELECTED_FILL } as SlotPaint, filled, filter: SELECTED_GLOW_FILTER, picked: true };

    return { paint: paint(filled), filled, filter: undefined, picked: false };
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
      <svg
        viewBox={`${VIEW_ORIGIN.x} ${VIEW_ORIGIN.y} ${VIEW} ${VIEW}`}
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Stroke divided by scale, so the ring matches the grid box's width. */}
        <path
          d={OUTLINE_PATH}
          transform={OUTLINE_TRANSFORM}
          fill={palette.body}
          stroke={palette.ring}
          strokeWidth={(RING_WIDTH * UNIT) / OUTLINE_SCALE}
          strokeLinejoin="round"
        />

        {/* One circle per slot, labelled by position. */}
        {Object.entries(SLOT_CENTERS).map(([key, { x, y }]) => {
          const position = Number(key);
          const { paint, filled, filter, picked } = slotStyle(position);
          const blocked = filled && mode === SlotMode.Pick;
          const isHovered = hovered === position && !blocked;
          const cursor = blocked ? 'not-allowed' : 'pointer';

          const handleClick = (e: React.MouseEvent) => {
            e.stopPropagation();
            onSlotClick?.(position);
          };

          return (
            // Non-interactive: the pointer passes through to the slot above.
            <Tooltip key={position} title={slotTitle(position)} arrow placement="top" disableInteractive>
              <g
                data-position={position}
                onClick={disableSlotClick ? undefined : handleClick}
                onMouseEnter={disableSlotClick ? undefined : () => hover(position)}
                onMouseLeave={disableSlotClick ? undefined : () => hover(null)}
                style={{
                  cursor: disableSlotClick ? 'default' : cursor,
                  transition: 'all 0.2s ease-in-out',
                  filter,
                }}
              >
                {!disableSlotClick && <circle cx={x} cy={y} r={HIT_RADIUS} fill="transparent" />}
                <circle
                  cx={x}
                  cy={y}
                  r={SLOT_RADIUS}
                  fill={paint.fill}
                  stroke={picked ? palette.label : palette.line}
                  strokeWidth={(isHovered || picked ? HOVER_LINE_WIDTH : LINE_WIDTH) * UNIT}
                  strokeDasharray={paint.dash}
                />
                <text
                  x={x}
                  y={y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontFamily="sans-serif"
                  fontWeight={700}
                  fontSize={FONT}
                  fill={LABEL_COLOR}
                  stroke={palette.label}
                  strokeWidth={FONT * LABEL_OUTLINE}
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
