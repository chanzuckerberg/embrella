'use client';

/**
 * Add a grid box to a puck slot.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Box, TextField, Typography } from '@mui/material';
import { PuckList, UserList } from '@app/common/types/gridLogging';
import {
  useCreateGridBox,
  useGridLoggingChoices,
  useGridLoggingPuckSlots,
  useGridLoggingUserList,
} from '@app/common/hooks/useGridLogging';
import { GridLoggingChoicesResponse } from '@app/common/types/gridLogging/config/choices';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { GridBoxSize, GridBoxSVG } from './GridBoxSvg';
import { defaultNumbering } from './gridBoxLayout';
import { ColorDropdown, FIELD_HEIGHT, NumberingDropdown, SizeDropdown } from './StyleDropdowns';
import { SlotPicker } from './SlotPicker';

const PREVIEW_SIZE = 160;
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

interface AddGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UserList | null;
  puck?: PuckList | null;
  positionInPuck?: number;
  onGridBoxCreated?: (slotPosition: number) => void;
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

  // Opened from the header button: default to the first free slot.
  const firstFree = slotsData?.slots.find((slot) => slot.status !== FILLED)?.position;
  const position = draft.position || firstFree || '';
  const name = draft.name ?? suggestName(puck?.name, position);

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

  const isFormValid = Boolean(name && draft.numbering && puck && position && choicesLoaded && usersLoaded);

  const handleSave = async () => {
    if (!isFormValid || !puck || !position) return;

    const result = await createGridBox({
      puck_id: puck.id,
      puckName: puck.name,
      gridBoxName: name,
      color: draft.color,
      numbering: draft.numbering,
      position_in_puck: position,
      max_grids: draft.maxGrids,
    });
    if (!result) return;

    onClose();
    onGridBoxCreated?.(position);
  };

  const handleNameKey = (event: React.KeyboardEvent) => {
    if (event.key !== ENTER) return;

    event.preventDefault();
    handleSave();
  };

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
          // minmax(0, …): the column never grows past the dialog for long values (e.g. U-counter-clockwise).
          gridTemplateColumns: `${PREVIEW_SIZE}px minmax(0, 1fr)`,
          columnGap: ROW_GAP,
          rowGap: ROW_GAP,
          alignItems: 'start',
        }}
      >
        {/* Live preview spans the three style rows. */}
        <Box sx={{ gridColumn: 1, gridRow: '1 / span 3', alignSelf: 'center' }}>
          <GridBoxSVG
            size={PREVIEW_SIZE}
            maxGrids={draft.maxGrids}
            numbering={draft.numbering}
            color={draft.color}
            disableGridClick
          />
        </Box>

        <Box sx={{ gridColumn: 2 }}>
          <Labeled label="Size">
            <SizeDropdown value={draft.maxGrids} onChange={setSize} />
          </Labeled>
        </Box>
        <Box sx={{ gridColumn: 2 }}>
          <Labeled label="Color">
            <ColorDropdown choices={choices} value={draft.color} onChange={(color) => update({ color })} />
          </Labeled>
        </Box>
        <Box sx={{ gridColumn: 2 }}>
          <Labeled label="Numbering">
            <NumberingDropdown
              choices={choices}
              maxGrids={draft.maxGrids}
              value={draft.numbering}
              onChange={(numbering) => update({ numbering })}
            />
          </Labeled>
        </Box>

        <Box sx={{ gridColumn: 1, mt: PLACEMENT_EXTRA_GAP }}>
          <Labeled label="Position">
            <SlotPicker
              puck={puck ?? undefined}
              slots={slotsData}
              value={position}
              onChange={(slot) => update({ position: slot })}
            />
          </Labeled>
        </Box>
        <Box sx={{ gridColumn: 2, mt: PLACEMENT_EXTRA_GAP }}>
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
