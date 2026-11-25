'use client';

/**
 * Visual location picker in a dialog.
 *
 *   ┌──────────────────────────────────────────────┐
 *   │ Title                                         │
 *   │ [🔍 Search grid, box or puck              ]   │
 *   │ All dewars ▾ › All canes ▾ › My pucks ▾       │  ← filters; in a puck: … › Pucks › 49 › Slot 1
 *   │ puck list  │  puck drawing  │  box + names    │
 *   │ Not here? Show pucks with my grids · all      │
 *   │ [tray, multi only]                            │
 *   │                          [Cancel] [Use …]     │
 *   └──────────────────────────────────────────────┘
 */

import React, { useContext } from 'react';
import { Alert, Box } from '@mui/material';
import { Button, Dialog, DialogContent, DialogTitle } from '@czi-sds/components';
import { UserContext } from '@app/common/context/UserProvider';
import { pickLabel } from './labels';
import { LocationSearch } from './LocationSearch';
import { NotHere } from './NotHere';
import { PickerCrumbs } from './PickerCrumbs';
import { PickPane } from './PickPane';
import { PuckList } from './PuckList';
import { SelectionTray } from './SelectionTray';
import { PickedLocation, PickerStart, PickTarget, SelectMode, TrashedGrid } from './types';
import { usePickerNav } from './usePickerNav';
import { useSelection } from './useSelection';

const ANY = () => true;
const SPACE = { section: '16px', inline: '12px' };

const defaultConfirm = (picks: PickedLocation[], mode: SelectMode) => {
  if (!picks.length) return 'Pick a location';
  if (mode === SelectMode.Single) return `Use ${pickLabel(picks[0])}`;

  return `Use ${picks.length}`;
};

export interface LocationPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (picks: PickedLocation[]) => void;
  title: string;
  target: PickTarget;
  mode?: SelectMode;
  capacity?: number; // multi only
  trayTitle?: string; // multi only, e.g. "Cassette"
  start?: PickerStart;
  initial?: PickedLocation[];
  canPick?: (pick: PickedLocation) => boolean; // e.g. only grids a session may use
  confirmLabel?: (picks: PickedLocation[]) => string;
  error?: string | null; // e.g. a failed move; shown above the buttons
  onDismissError?: () => void;
  busy?: boolean; // confirm in flight: disables the primary button
  onPickTrashed?: (grid: TrashedGrid) => void; // Grid target, single only: search also offers trashed grids
}

// Mounted per open, so filters, path and picks start fresh each time.
const PickerBody = ({
  onClose,
  onConfirm,
  target,
  mode = SelectMode.Single,
  capacity = 1,
  trayTitle = 'Selected',
  start,
  initial,
  canPick = ANY,
  confirmLabel,
  error,
  onDismissError,
  busy = false,
  onPickTrashed,
}: Omit<LocationPickerDialogProps, 'open' | 'title'>) => {
  const user = useContext(UserContext);
  const userId = user ? Number(user.id) : null;
  const nav = usePickerNav(userId, target, start);
  const selection = useSelection(mode, capacity, initial);
  const { picks } = selection;

  // A trashed grid has no spot, so only a single grid pick can take one.
  const pickTrashed = target === PickTarget.Grid && mode === SelectMode.Single ? onPickTrashed : undefined;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: SPACE.section, pt: '8px' }}>
      <LocationSearch nav={nav} selection={selection} canPick={canPick} onPickTrashed={pickTrashed} />
      <PickerCrumbs nav={nav} userId={userId} />

      {nav.puck ? (
        <PickPane nav={nav} selection={selection} canPick={canPick} />
      ) : (
        <>
          <PuckList nav={nav} userId={userId} />
          <NotHere nav={nav} />
        </>
      )}

      {mode === SelectMode.Multi && <SelectionTray selection={selection} title={trayTitle} />}

      {Boolean(error) && (
        <Alert severity="error" onClose={onDismissError}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: SPACE.inline }}>
        <Button sdsType="secondary" sdsStyle="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button sdsType="primary" sdsStyle="solid" disabled={!picks.length || busy} onClick={() => onConfirm(picks)}>
          {confirmLabel ? confirmLabel(picks) : defaultConfirm(picks, mode)}
        </Button>
      </Box>
    </Box>
  );
};

export const LocationPickerDialog = ({ open, title, ...rest }: LocationPickerDialogProps) => (
  <Dialog open={open} onClose={rest.onClose} sdsSize="s">
    <DialogTitle title={title} onClose={rest.onClose} />
    <DialogContent>{open && <PickerBody {...rest} />}</DialogContent>
  </Dialog>
);
