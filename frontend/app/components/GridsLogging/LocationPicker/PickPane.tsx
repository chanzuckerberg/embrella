'use client';

/**
 * The open puck or box, drawn and clickable per target:
 *   puck step  Grid / EmptyPosition: filled slot opens its box · EmptySlot: empty slot is the pick
 *   box step   Grid: occupied position · EmptyPosition: free position
 *
 * Box step: drawing left, names right, so an 8-grid box stays about as tall as its drawing.
 *   ┌─────────┬──────────────────────┐
 *   │ (box)   │ ☐ Select all (4)     │  ← multi only
 *   │         │ ☑ 1  WT_RPE_…_G1     │
 *   │         │ ☐ 2  WT_RPE_…_G2     │
 *   └─────────┴──────────────────────┘
 */

import React, { useState } from 'react';
import { Box, Checkbox, List, ListItemButton, ListItemText, Tooltip, Typography } from '@mui/material';
import { useGridLoggingGridBoxDetail, useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging';
import { Position } from '@app/common/types/gridLogging/details/gridBoxDetails';
import { describeSlot, PuckSVG, SlotMode } from '@app/components/GridsLogging/Pucks/PuckSvg';
import { GridBoxSize, GridBoxSVG } from '@app/components/GridsLogging/GridBox/GridBoxSvg';
import { Membership, PickedLocation, PickTarget, SelectMode } from './types';
import { PickerNav } from './usePickerNav';
import { Selection } from './useSelection';

const FILLED = 'filled';
const PUCK_SIZE = 260;
const BOX_SIZE = 200;
const POSITION_WIDTH = '24px';
const DEFAULT_GRIDS = 4;

interface PickPaneProps {
  nav: PickerNav;
  selection: Selection;
  canPick?: (pick: PickedLocation) => boolean;
}

export const PickPane = ({ nav, selection, canPick = () => true }: PickPaneProps) => {
  const { nav: state, actions, puck, target } = nav;
  const [hovered, setHovered] = useState<number | null>(null);
  const { slotsData } = useGridLoggingPuckSlots(puck?.id);
  const { gridBoxData } = useGridLoggingGridBoxDetail(puck?.id, state.slot ?? undefined);

  if (!puck) return null;

  const isMulti = selection.mode === SelectMode.Multi;
  const isFilled = (slot: number) => slotsData?.slots.some((s) => s.position === slot && s.status === FILLED);

  // Box step: one pick per clickable position.
  const box = gridBoxData?.grid_box;
  const toPick = (p: Position): PickedLocation | null => {
    if (state.slot === null || !box) return null;

    const at = {
      puckId: puck.id,
      puckName: puck.name,
      slot: state.slot,
      gridBoxId: box.grid_box_id,
      boxName: box.name,
      position: p.q,
    };
    if (target === PickTarget.Grid && p.occupied && p.grid_id !== undefined) {
      return { key: `g${p.grid_id}`, ...at, gridId: p.grid_id, gridName: p.grid_name };
    }
    if (target === PickTarget.EmptyPosition && !p.occupied) return { key: `p${puck.id}-s${state.slot}-q${p.q}`, ...at };

    return null;
  };

  // Puck step for EmptySlot: the slot itself is the pick.
  const slotPick = (slot: number): PickedLocation => ({
    key: `p${puck.id}-s${slot}`,
    puckId: puck.id,
    puckName: puck.name,
    slot,
  });

  const clickSlot = (slot: number) => {
    if (target !== PickTarget.EmptySlot) {
      if (isFilled(slot)) actions.openSlot(slot);
      return;
    }

    const pick = slotPick(slot);
    if (isFilled(slot) || !canPick(pick)) return;

    selection.toggle(pick);
  };

  // Puck step status: hovered slot, else what this puck offers and where picks sit.
  const picksHere = selection.picks.filter((p) => p.puckId === puck.id);
  const summary =
    target === PickTarget.EmptySlot
      ? `${slotsData?.slot_summary.empty_count ?? 0} of ${slotsData?.slot_summary.total ?? 0} free`
      : `${slotsData?.slot_summary.filled_count ?? 0} boxes`;
  const pickedSlots = [...new Set(picksHere.map((p) => p.slot))].join(', ');
  const idleStatus = pickedSlots && isMulti ? `${summary} · picked in slot ${pickedSlots}` : summary;
  const status = slotsData && hovered !== null ? describeSlot(slotsData.slots, hovered) : idleStatus;

  if (state.slot === null || target === PickTarget.EmptySlot) {
    const highlighted = target === PickTarget.EmptySlot ? picksHere[0]?.slot : undefined;

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
        <PuckSVG
          puck={puck}
          slots={slotsData?.slots}
          size={PUCK_SIZE}
          mode={target === PickTarget.EmptySlot ? SlotMode.Pick : SlotMode.View}
          highlightedSlot={highlighted}
          onSlotHover={setHovered}
          onSlotClick={clickSlot}
        />
        <Typography variant="body2">{status}</Typography>
      </Box>
    );
  }

  const positions = [...(box?.positions ?? [])].sort((a, b) => a.q - b.q);
  const boxPicks = positions.map(toPick).filter((p): p is PickedLocation => p !== null && canPick(p));
  const pickedHere = boxPicks.filter((p) => selection.isPicked(p.key));

  // Select all: adds the rest of the box if it fits, else nothing; unchecks when all are in.
  const allPicked = boxPicks.length > 0 && pickedHere.length === boxPicks.length;
  const allFits = boxPicks.length - pickedHere.length <= selection.room;
  const toggleAll = () => selection.setMany(boxPicks, allPicked ? Membership.Remove : Membership.Add);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <Box sx={{ flexShrink: 0 }}>
        <GridBoxSVG
          size={BOX_SIZE}
          gridBoxData={gridBoxData}
          maxGrids={(box?.max_grids ?? DEFAULT_GRIDS) as GridBoxSize}
          numbering={box?.numbering}
          selectedGrids={selection.picks
            .filter((p) => p.puckId === puck.id && p.slot === state.slot && p.position !== undefined)
            .map((p) => p.position as number)}
          onGridClick={(q) => {
            const p = positions.find((pos) => pos.q === q);
            const pick = p && toPick(p);
            if (pick && canPick(pick)) selection.toggle(pick);
          }}
        />
      </Box>

      <List dense sx={{ flex: 1, minWidth: 0, py: '0px' }}>
        {isMulti && (
          <Tooltip title={allFits || allPicked ? '' : `Only ${selection.room} slots left`}>
            <span>
              <ListItemButton
                disabled={!boxPicks.length || (!allFits && !allPicked)}
                onClick={toggleAll}
                sx={{ py: '0px', borderRadius: '4px', borderBottom: '1px solid', borderColor: 'grey.200' }}
              >
                <Checkbox
                  size="small"
                  edge="start"
                  checked={allPicked}
                  indeterminate={pickedHere.length > 0 && !allPicked}
                  tabIndex={-1}
                  sx={{ p: '4px', mr: '4px' }}
                />
                <ListItemText primary={`Select all in box (${boxPicks.length})`} />
              </ListItemButton>
            </span>
          </Tooltip>
        )}

        {positions.map((p) => {
          const pick = toPick(p);
          const allowed = pick !== null && canPick(pick);
          const picked = pick !== null && selection.isPicked(pick.key);
          const blocked = isMulti && !picked && selection.room <= 0;

          return (
            <ListItemButton
              key={p.q}
              disabled={!allowed || blocked}
              selected={picked}
              onClick={() => pick && selection.toggle(pick)}
              sx={{ py: isMulti ? '0px' : '2px', borderRadius: '4px' }}
            >
              {isMulti && (
                <Checkbox
                  size="small"
                  edge="start"
                  checked={picked}
                  tabIndex={-1}
                  disabled={!allowed}
                  sx={{ p: '4px', mr: '4px' }}
                />
              )}
              <Typography variant="body2" color="text.secondary" sx={{ width: POSITION_WIDTH, flexShrink: 0 }}>
                {p.q}
              </Typography>
              <ListItemText
                primary={p.occupied ? p.grid_name : 'Free'}
                title={p.grid_name}
                primaryTypographyProps={{ noWrap: true, sx: { fontWeight: picked ? 600 : 400 } }}
              />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );
};
