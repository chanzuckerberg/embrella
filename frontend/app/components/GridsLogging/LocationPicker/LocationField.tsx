'use client';

/**
 * Dropdown-style form field showing the picked location, e.g. "49 · slot 3"
 * (puck 49, slot 3). Clicking it opens the location picker dialog.
 */

import React, { useState } from 'react';
import { InputDropdown } from '@czi-sds/components';
import { pickLabel } from './labels';
import { LocationPickerDialog } from './LocationPickerDialog';
import { PickedLocation, PickerStart, PickTarget } from './types';

const FILL = '100%';

interface LocationFieldProps {
  label: string;
  placeholder: string;
  dialogTitle: string;
  target: PickTarget;
  value: PickedLocation | null;
  onChange: (pick: PickedLocation) => void;
  start?: PickerStart;
  canPick?: (pick: PickedLocation) => boolean;
  disabled?: boolean;
}

export const LocationField = ({
  label,
  placeholder,
  dialogTitle,
  target,
  value,
  onChange,
  start,
  canPick,
  disabled,
}: LocationFieldProps) => {
  const [open, setOpen] = useState(false);

  const confirm = (picks: PickedLocation[]) => {
    setOpen(false);
    if (!picks[0]) return;

    onChange(picks[0]);
  };

  return (
    <>
      <InputDropdown
        label={label}
        sdsType="value"
        sdsStyle="square"
        width={FILL}
        disabled={disabled}
        value={value ? pickLabel(value) : placeholder}
        state={open ? 'open' : 'default'}
        onClick={() => setOpen(true)}
      />
      <LocationPickerDialog
        open={open}
        onClose={() => setOpen(false)}
        onConfirm={confirm}
        title={dialogTitle}
        target={target}
        start={value ? { puckId: value.puckId, slot: value.slot } : start}
        initial={value ? [value] : []}
        canPick={canPick}
      />
    </>
  );
};
