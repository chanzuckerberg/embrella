'use client';

/**
 * Add a grid box to a puck slot.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Box, TextField, Typography, useMediaQuery } from '@mui/material';
import { PuckList, UserList } from '@app/common/types/gridLogging';
import {
  useCreateGridBox,
  useGridLoggingChoices,
  useGridLoggingPuckSlots,
  useGridLoggingUserList,
} from '@app/common/hooks/useGridLogging';
import { GridLoggingChoicesResponse } from '@app/common/types/gridLogging/config/choices';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { GridBoxFit, GridBoxSize, GridBoxSVG } from './GridBoxSvg';
import { defaultNumbering } from './gridBoxLayout';
import { ColorDropdown, FIELD_HEIGHT, NumberingDropdown, SizeDropdown } from './StyleDropdowns';
import { LocationField, PickTarget } from '../LocationPicker';

const PREVIEW_SIZE = 160;
const PREVIEW_SIZE_NARROW = 128;

// Below this the xs dialog (400px + 2×32px margin) shrinks and the side column squeezes fields; stack instead.
const NARROW_QUERY = '(max-width: 463px)';

const FILLED = 'filled';
const ENTER = 'Enter';

// Explicit px: numeric sx spacing maps oddly under the SDS theme.
const ROW_GAP = '12px';
const LABEL_GAP = '4px';

// Row gap + this = 24px section gap above the placement row.
const PLACEMENT_EXTRA_GAP = '12px';

// Section labels match field text (14px); SDS body1/body2 are 13/12px.
const LABEL_SX = { fontSize: '14px', fontWeight: 600 };

// Fallbacks until choices load; the backend's grid_box_defaults wins.
const FALLBACK = { maxGrids: 8 as GridBoxSize, color: '00cdf5', numbering: 'col' };

interface Draft {
  maxGrids: GridBoxSize;
  color: string;
  numbering: string;
  position: number | '';
  // Picked from another puck in the location picker; null = the puck this dialog opened on.
  destination: { id: number; name: string } | null;
  // null = use the suggested name.
  name: string | null;
}

const initialDraft = (choices: GridLoggingChoicesResponse | undefined, position?: number): Draft => {
  const defaults = choices?.grid_box_defaults;

  return {
    maxGrids: (defaults?.max_grids ?? FALLBACK.maxGrids) as GridBoxSize,
    color: defaults?.color ?? FALLBACK.color,
    numbering: defaults?.numbering ?? FALLBACK.numbering,
    position: position ?? '',
    destination: null,
    name: null,
  };
};

// Suggested name, e.g. puck 4 slot 2 → "Puck4-Pos2".
const suggestName = (puckName?: string, position?: number | '') =>
  puckName && position ? `Puck${puckName}-Pos${position}` : '';

// Label above its field, 4px apart.
const Labeled = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: LABEL_GAP, minWidth: 0 }}>
    <Typography variant="body1" sx={LABEL_SX}>
      {label}
    </Typography>
    {children}
  </Box>
);

/**
 * Cell placement per layout. DOM order is the same in both, so tab order is too.
 *
 *   Wide                     Narrow
 *   ┌───────┬──────────┐     ┌─────────────┐
 *   │       │ Size     │     │   preview   │
 *   │preview│ Color    │     │ Size │Color │
 *   │       │ Numbering│     │ Numbering   │
 *   ├───────┼──────────┤     │ Position    │
 *   │Positn │ Name     │     │ Name        │
 *   └───────┴──────────┘     └─────────────┘
 */
const WIDE = {
  // minmax(0, …): the column never grows past the dialog for long values (e.g. U-counter-clockwise).
  columns: `${PREVIEW_SIZE}px minmax(0, 1fr)`,
  preview: { gridColumn: 1, gridRow: '1 / span 3', alignSelf: 'center' },
  size: { gridColumn: 2 },
  color: { gridColumn: 2 },
  numbering: { gridColumn: 2 },
  position: { gridColumn: 1, mt: PLACEMENT_EXTRA_GAP },
  name: { gridColumn: 2, mt: PLACEMENT_EXTRA_GAP },
};

// Size and Color share a row: short values (longest "Neon Pink") fit half width, saving a row on short screens.
const FULL_ROW = '1 / -1';
const NARROW = {
  columns: 'repeat(2, minmax(0, 1fr))',
  preview: { gridColumn: FULL_ROW, justifySelf: 'center' },
  size: {},
  color: {},
  numbering: { gridColumn: FULL_ROW },
  position: { gridColumn: FULL_ROW, mt: PLACEMENT_EXTRA_GAP },
  name: { gridColumn: FULL_ROW },
};

interface AddGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UserList | null;
  puck?: PuckList | null;
  positionInPuck?: number;
  onGridBoxCreated?: (slotPosition: number, puckId: number) => void;
}

export const AddGridBox: React.FC<AddGridBoxProps> = ({
  open,
  onClose,
  selectedUser,
  puck,
  positionInPuck,
  onGridBoxCreated,
}) => {
  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();
  const { createGridBox, isCreating, error, clearError } = useCreateGridBox();
  const { slotsData, refetch: refetchPuckSlots } = useGridLoggingPuckSlots(puck?.id);

  const [draft, setDraft] = useState<Draft>(() => initialDraft(choices, positionInPuck));
  const update = (patch: Partial<Draft>) => setDraft((prev) => ({ ...prev, ...patch }));

  // Reset when the dialog opens.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setDraft(initialDraft(choices, positionInPuck));
      clearError();
    }
  }

  useEffect(() => {
    if (open && puck?.id) {
      refetchPuckSlots();
    }
  }, [open, puck?.id, refetchPuckSlots]);

  // Opened from the header button: default to the first free slot of this puck.
  const firstFree = slotsData?.slots.find((slot) => slot.status !== FILLED)?.position;
  const position = draft.position || (draft.destination ? '' : firstFree) || '';
  const target = draft.destination ?? puck;
  const name = draft.name ?? suggestName(target?.name, position);

  // Switching size resets numbering to that size's default (e.g. 8 → col).
  const setSize = (maxGrids: GridBoxSize) => update({ maxGrids, numbering: defaultNumbering(choices, maxGrids) });

  // Focus Name once its suggestion is ready, text selected so typing replaces it.
  // Done here, not via autoFocus: the dialog grabs focus on open, and the suggestion waits on slot data.
  const nameRef = useRef<HTMLInputElement>(null);
  const hasName = Boolean(name);
  useEffect(() => {
    if (!open || !hasName) return;

    const timer = setTimeout(() => {
      nameRef.current?.focus();
      nameRef.current?.select();
    });

    return () => clearTimeout(timer);
  }, [open, hasName]);

  const isFormValid = Boolean(name && draft.numbering && target && position && choicesLoaded && usersLoaded);

  const handleSave = async () => {
    if (!isFormValid || !target || !position) return;

    const result = await createGridBox({
      puck_id: target.id,
      puckName: target.name,
      gridBoxName: name,
      color: draft.color,
      numbering: draft.numbering,
      position_in_puck: position,
      max_grids: draft.maxGrids,
    });
    if (!result) return;

    onClose();
    onGridBoxCreated?.(position, target.id);
  };

  const handleNameKey = (event: React.KeyboardEvent) => {
    if (event.key !== ENTER) return;

    event.preventDefault();
    handleSave();
  };

  const isNarrow = useMediaQuery(NARROW_QUERY);
  const layout = isNarrow ? NARROW : WIDE;

  const subtitle = [puck?.name, selectedUser?.full_name].filter(Boolean).join(' · ');

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Add a Grid Box"
      subtitle={subtitle}
      onSave={handleSave}
      saveButtonText="Add grid box"
      isSubmitting={isCreating}
      disabled={!isFormValid}
    >
      {Boolean(error) && <Alert severity="error">{error}</Alert>}

      {/* One grid so edges line up; DOM order = tab order (size → color → numbering → position → name). */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: layout.columns,
          columnGap: ROW_GAP,
          rowGap: ROW_GAP,
          alignItems: 'start',
        }}
      >
        {/* Live preview: spans the three style rows when wide, on top when narrow. Tight so its edge lines up with Position. */}
        <Box sx={layout.preview}>
          <GridBoxSVG
            size={isNarrow ? PREVIEW_SIZE_NARROW : PREVIEW_SIZE}
            fit={GridBoxFit.Tight}
            maxGrids={draft.maxGrids}
            numbering={draft.numbering}
            color={draft.color}
            disableGridClick
          />
        </Box>

        <Box sx={layout.size}>
          <Labeled label="Size">
            <SizeDropdown value={draft.maxGrids} onChange={setSize} />
          </Labeled>
        </Box>
        <Box sx={layout.color}>
          <Labeled label="Color">
            <ColorDropdown choices={choices} value={draft.color} onChange={(color) => update({ color })} />
          </Labeled>
        </Box>
        <Box sx={layout.numbering}>
          <Labeled label="Numbering">
            <NumberingDropdown
              choices={choices}
              maxGrids={draft.maxGrids}
              value={draft.numbering}
              onChange={(numbering) => update({ numbering })}
            />
          </Labeled>
        </Box>

        <Box sx={layout.position}>
          <Labeled label="Position">
            {/* Opens on this puck; any free slot in any puck can take the new box. */}
            <LocationField
              label="Position"
              placeholder="Pick a slot"
              dialogTitle="Pick a slot"
              target={PickTarget.EmptySlot}
              value={
                target && position
                  ? { key: `p${target.id}-s${position}`, puckId: target.id, puckName: target.name, slot: position }
                  : null
              }
              start={puck ? { puckId: puck.id } : undefined}
              onChange={(pick) =>
                update({
                  position: pick.slot,
                  destination: pick.puckId === puck?.id ? null : { id: pick.puckId, name: pick.puckName },
                })
              }
            />
          </Labeled>
        </Box>
        <Box sx={layout.name}>
          <Labeled label="Name">
            <TextField
              required
              size="small"
              fullWidth
              inputRef={nameRef}
              onKeyDown={handleNameKey}
              value={name}
              onChange={(event) => update({ name: event.target.value })}
              sx={{ '& .MuiInputBase-root': { height: FIELD_HEIGHT } }}
            />
          </Labeled>
        </Box>
      </Box>
    </BaseFormDialog>
  );
};
