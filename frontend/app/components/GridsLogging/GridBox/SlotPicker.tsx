'use client';

/**
 * Puck slot field: a dropdown of slots, plus a puck-drawing dialog for picking visually.
 */

import React, { useState } from 'react';
import { Box, Tooltip, Typography } from '@mui/material';
import { Button, Dialog, DialogContent, DialogTitle, DropdownMenu, Icon, InputDropdown } from '@czi-sds/components';
import { useGridLoggingCaneList } from '@app/common/hooks/useGridLogging';
import { PuckList, PuckSlotsResponse } from '@app/common/types/gridLogging';
import { describeSlot, PuckSVG, SlotMode } from '../Pucks/PuckSvg';

const FILLED = 'filled';
const FILL = '100%';
const MENU_MIN_WIDTH = 200;
const PUCK_PREVIEW = 280;
const FUTURE_HINT = 'Coming soon';

// Menu entry that opens the dialog instead of picking a slot.
const PICK_ON_PUCK = -1;

// Explicit px: numeric sx spacing maps oddly under the SDS theme.
const SPACE = { section: '24px', inline: '12px' };

const isFree = (slots: PuckSlotsResponse | undefined, position: number) =>
  slots?.slots.find((slot) => slot.position === position)?.status !== FILLED;

// SDS options are either text (+ details) or custom content, never both.
// No boolean fields: SDS spreads option props onto the menu item DOM.
type SlotOption =
  | { name: string; position: number; details?: string; component?: undefined }
  | { name: string; position: number; component: React.ReactNode; details?: undefined };

// "Pick on puck" row: label left, open icon right.
const PickOnPuckRow = () => (
  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
    <span>Pick on Puck</span>
    <Icon sdsIcon="Open" sdsSize="s" color="gray" />
  </Box>
);

// First menu item only: divider below; SDS content wrappers stretch so the icon sits at the right edge.
const ENTRY_STYLE = {
  '& > li:first-of-type': { borderBottom: '1px solid', borderColor: 'grey.300' },
  '& > li:first-of-type > span:last-of-type, & > li:first-of-type .primary-text': { flex: 1 },
};

const toOption = (position: number, details: string): SlotOption => ({ name: `Slot ${position}`, details, position });

// Free slots first, then filled ones with their box name.
const slotOptions = (slots?: PuckSlotsResponse): SlotOption[] => {
  const all = slots?.slots ?? [];
  const free = all.filter((slot) => slot.status !== FILLED).map((slot) => toOption(slot.position, 'Free'));
  const filled = all
    .filter((slot) => slot.status === FILLED)
    .map((slot) => toOption(slot.position, slot.grid_box_name ?? 'Filled'));

  return [...free, ...filled];
};

interface SlotPickerProps {
  puck?: PuckList;
  slots?: PuckSlotsResponse;
  value: number | '';
  onChange: (position: number) => void;
}

export const SlotPicker = ({ puck, slots, value, onChange }: SlotPickerProps) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pending, setPending] = useState<number | ''>(value);
  const [hovered, setHovered] = useState<number | null>(null);
  const { canes } = useGridLoggingCaneList();

  // Location trail, outermost first; dewar shows its id until the API sends its name, skipped when unset.
  const cane = canes.find((c) => c.id === puck?.cane);
  const trail = [cane?.dewar && `Dewar ${cane.dewar}`, cane && `Cane ${cane.name}`, puck?.name]
    .filter(Boolean)
    .join(' › ');

  const options = slotOptions(slots);
  const menuOptions: SlotOption[] = [
    { name: 'Pick on puck', position: PICK_ON_PUCK, component: <PickOnPuckRow /> },
    ...options,
  ];
  const selected = options.find((option) => option.position === value) ?? null;

  // Under the puck: hovered slot's occupant, else the free count. Replaces a tooltip that would cover the slot above.
  const freeCount = `${slots?.slot_summary.empty_count ?? 0} of ${slots?.slot_summary.total ?? 0} free`;
  const status = slots && hovered !== null ? describeSlot(slots.slots, hovered) : freeCount;

  const openDialog = () => {
    setPending(value);
    setDialogOpen(true);
  };

  const handlePick = (_event: React.SyntheticEvent, option: SlotOption | null) => {
    setAnchorEl(null);
    if (!option) return;

    if (option.position === PICK_ON_PUCK) {
      openDialog();
      return;
    }

    onChange(option.position);
  };

  const confirmDialog = () => {
    setDialogOpen(false);
    if (!pending) return;

    onChange(pending);
  };

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <InputDropdown
          label="Position"
          sdsType="value"
          sdsStyle="square"
          width={FILL}
          value={value ? `Slot ${value}` : 'Pick a slot'}
          state={anchorEl ? 'open' : 'default'}
          onClick={(event: React.MouseEvent<HTMLElement>) => setAnchorEl(anchorEl ? null : event.currentTarget)}
        />
        <Typography variant="caption" color="text.secondary">
          {trail}
        </Typography>
      </Box>

      <DropdownMenu<SlotOption, false, false, false>
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        width={Math.max(anchorEl?.clientWidth ?? 0, MENU_MIN_WIDTH)}
        options={menuOptions}
        value={selected}
        isOptionEqualToValue={(a, b) => a.position === b.position}
        getOptionDisabled={(option) => option.position !== PICK_ON_PUCK && !isFree(slots, option.position)}
        ListboxProps={{ sx: ENTRY_STYLE }}
        onChange={handlePick}
        onClickAway={() => setAnchorEl(null)}
      />

      {/* xs (400px) matches the Add dialog; a child dialog should not be wider than its parent. */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} sdsSize="xs">
        <DialogTitle title="Pick a slot" onClose={() => setDialogOpen(false)} />
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: SPACE.section, pt: '8px' }}>
            {/* Where the box will go; picking another puck is a planned add-on. */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: SPACE.inline,
                px: '12px',
                py: '8px',
                bgcolor: 'grey.50',
                borderRadius: '4px',
              }}
            >
              <Typography variant="body2">{trail}</Typography>
              <Tooltip title={FUTURE_HINT}>
                <span>
                  <Button sdsType="secondary" sdsStyle="minimal" disabled>
                    Other puck
                  </Button>
                </span>
              </Tooltip>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              {puck && (
                <PuckSVG
                  puck={puck}
                  slots={slots?.slots}
                  size={PUCK_PREVIEW}
                  highlightedSlot={pending || undefined}
                  mode={SlotMode.Pick}
                  onSlotHover={setHovered}
                  onSlotClick={(position) => isFree(slots, position) && setPending(position)}
                />
              )}
            </Box>

            <Typography variant="body2" sx={{ textAlign: 'center' }}>
              {status}
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: SPACE.inline }}>
              <Button sdsType="secondary" sdsStyle="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button sdsType="primary" sdsStyle="solid" disabled={!pending} onClick={confirmDialog}>
                {pending ? `Use slot ${pending}` : 'Use slot'}
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};
