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
 */

import React, { useMemo, useState } from 'react';
import { Box, Link, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import {
  LocationPickerDialog,
  PickedLocation,
  pickLabel,
  PickTarget,
} from '@app/components/GridsLogging/LocationPicker';
import { GridOption } from '../types';

// Location line, e.g. "49 · slot 1 · pos 4": pickLabel without the grid name.
const LOCATION_OF_PICK = (pick: PickedLocation) => pickLabel({ ...pick, gridName: undefined });

interface GridFieldProps {
  grids: GridOption[];
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

export const GridField = ({ grids, gridId, onChange, labelClass }: GridFieldProps) => {
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState<PickedLocation | null>(null);

  // Only grids this form offers are pickable, so session rules stay server-side.
  const gridIds = useMemo(() => new Set(grids.map((g) => g.id)), [grids]);
  const defaultGrid = grids.find((g) => g.is_default);
  const selected = grids.find((g) => g.id === gridId);
  const isDefault = Boolean(selected && selected.id === defaultGrid?.id);

  // Location line: from the pick when we have it; the default grid has none worth showing.
  const where = pick && pick.gridId === gridId ? LOCATION_OF_PICK(pick) : null;

  const confirm = ([picked]: PickedLocation[]) => {
    setOpen(false);
    if (!picked?.gridId) return;

    setPick(picked);
    onChange(picked.gridId);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div className={labelClass}>Grid</div>

      {!selected && (
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

      {selected && (
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
            <Typography variant="body1" noWrap sx={{ fontWeight: 600 }}>
              {pick && pick.gridId === gridId ? pickLabel(pick) : selected.name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {isDefault ? 'Placeholder for an unknown grid' : (where ?? selected.display_name)}
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
        start={where && pick ? { puckId: pick.puckId, slot: pick.slot } : undefined}
        initial={pick && pick.gridId === gridId ? [pick] : []}
        canPick={(p) => p.gridId !== undefined && gridIds.has(p.gridId)}
      />
    </Box>
  );
};
