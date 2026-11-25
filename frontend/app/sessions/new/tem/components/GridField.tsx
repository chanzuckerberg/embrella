'use client';

/**
 * Grid choice for a TEM session: picked by where it sits, never pre-filled.
 *
 *   empty:   [📍 Pick grid by location]
 *            Don't know which grid? Use the default grid
 *   picked:  ┌──────────────────────────────────┐
 *            │ WT_RPE_8/26/26_B1_G4      Change │
 *            │ 49 · slot 1 · pos 4               │
 *            └──────────────────────────────────┘
 * The default grid is a last-resort placeholder, so it is a quiet link, not a choice in the list.
 * Trashed grids (old sessions) have no location: the picker's search offers them by name.
 *   picked:  │ WT_RPE_…_G4 (id=7)  [Trashed]         Change │
 *            │ User Name · Project                           │
 * Everything shown comes from the pick itself; the form loads no grid list.
 */

import React, { useState } from 'react';
import { Box, Link, Typography } from '@mui/material';
import { Button, Icon, Tag } from '@czi-sds/components';
import {
  LocationPickerDialog,
  PickedLocation,
  pickLabel,
  PickTarget,
  TrashedGrid,
} from '@app/components/GridsLogging/LocationPicker';
import { GridRef } from '../types';

// Location line, e.g. "49 · slot 1 · pos 4": pickLabel without the grid name.
const LOCATION_OF_PICK = (pick: PickedLocation) => pickLabel({ ...pick, gridName: undefined });
const DEFAULT_DETAIL = 'Placeholder for an unknown grid';

// What the card shows for the chosen grid; `pick` only for grids picked by location.
interface Chosen {
  gridId: number;
  name: string;
  detail: string;
  trashed: boolean;
  pick?: PickedLocation;
}

// Card for the current grid: the default placeholder, or whatever was last picked.
const cardFor = (gridId: number | null, defaultGrid: GridRef | null, chosen: Chosen | null): Chosen | null => {
  if (gridId === null) return null;
  if (gridId === defaultGrid?.id) return { gridId, name: defaultGrid.name, detail: DEFAULT_DETAIL, trashed: false };

  return chosen?.gridId === gridId ? chosen : null;
};

interface GridFieldProps {
  defaultGrid: GridRef | null;
  gridId: number | null;
  onChange: (gridId: number | null) => void;
  labelClass: string;
}

// Plain link that sits on the text baseline (button-links default to vertical-align: middle).
const TextLink = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) => (
  <Link
    component="button"
    type="button"
    variant="body2"
    underline="hover"
    onClick={onClick}
    sx={{ verticalAlign: 'baseline' }}
  >
    {children}
  </Link>
);

export const GridField = ({ defaultGrid, gridId, onChange, labelClass }: GridFieldProps) => {
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState<Chosen | null>(null);

  const card = cardFor(gridId, defaultGrid, chosen);
  const pick = card?.pick;

  const choose = (next: Chosen) => {
    setOpen(false);
    setChosen(next);
    onChange(next.gridId);
  };

  const confirm = ([picked]: PickedLocation[]) => {
    if (!picked?.gridId) {
      setOpen(false);
      return;
    }

    choose({
      gridId: picked.gridId,
      name: pickLabel(picked),
      detail: LOCATION_OF_PICK(picked),
      trashed: false,
      pick: picked,
    });
  };

  const pickTrashed = (grid: TrashedGrid) =>
    choose({ gridId: grid.id, name: grid.name, detail: grid.detail, trashed: true });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div className={labelClass}>Grid</div>

      {!card && (
        <>
          <Box>
            <Button
              sdsType="secondary"
              sdsStyle="outline"
              startIcon={<Icon sdsIcon="PinLocation" sdsSize="s" />}
              onClick={() => setOpen(true)}
            >
              Pick grid by location
            </Button>
          </Box>
          {defaultGrid && (
            <Typography variant="caption" color="text.secondary">
              Don&apos;t know which grid?{' '}
              <TextLink onClick={() => onChange(defaultGrid.id)}>Use the default grid</TextLink>
            </Typography>
          )}
        </>
      )}

      {card && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            px: '12px',
            py: '8px',
            border: '1px solid',
            borderColor: 'grey.300',
            borderRadius: '4px',
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <Typography variant="body1" noWrap sx={{ fontWeight: 600 }}>
                {card.name}
              </Typography>
              {card.trashed && <Tag label="Trashed" color="neutral" sdsType="secondary" sdsStyle="rounded" />}
            </Box>
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {card.detail}
            </Typography>
          </Box>
          <TextLink onClick={() => setOpen(true)}>Change</TextLink>
        </Box>
      )}

      <LocationPickerDialog
        open={open}
        onClose={() => setOpen(false)}
        onConfirm={confirm}
        title="Select grid"
        target={PickTarget.Grid}
        start={pick ? { puckId: pick.puckId, slot: pick.slot } : undefined}
        initial={pick ? [pick] : []}
        onPickTrashed={pickTrashed}
      />
    </Box>
  );
};
