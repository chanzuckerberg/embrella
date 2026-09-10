'use client';

/**
 * FreeTextOptionField - a dynamic-options field that also takes a typed value.
 *
 * Used where the listed options are a convenience, not the only valid input:
 * e.g. gain files listed from the session's camera directory, or an absolute
 * path to one elsewhere on the cluster.
 */

import { Autocomplete, TextField } from '@mui/material';
import type { FieldOption } from '@app/common/types/workflow';

interface FreeTextOptionFieldProps {
  name: string;
  label: string;
  value: string;
  options: FieldOption[];
  required?: boolean;
  helperText?: string;
  onChange: (name: string, value: string) => void;
}

const optionLabel = (option: FieldOption | string) => (typeof option === 'string' ? option : option.label);
// Autocomplete hands back a string for typed text, an option for a pick, null when cleared
const optionValue = (chosen: FieldOption | string | null) => {
  if (chosen === null) return '';
  return typeof chosen === 'string' ? chosen : chosen.value;
};

export function FreeTextOptionField({
  name,
  label,
  value,
  options,
  required = false,
  helperText,
  onChange,
}: FreeTextOptionFieldProps) {
  // The selected option, else the typed text as-is; keeps the input in sync with `value`
  const selected = options.find((option) => option.value === value) ?? value;
  // A listed option shows its label, which is not the value: lock the input so typing can't
  // corrupt it. Pick another option or clear (the X button) to start typing a path.
  const showsLabel = typeof selected !== 'string';

  return (
    <Autocomplete
      freeSolo
      options={options}
      value={selected}
      getOptionLabel={optionLabel}
      isOptionEqualToValue={(option, chosen) => optionValue(option) === optionValue(chosen)}
      onChange={(_, chosen) => onChange(name, optionValue(chosen))}
      onInputChange={(_, text, reason) => {
        if (reason === 'input') onChange(name, text);
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          inputProps={{ ...params.inputProps, readOnly: showsLabel }}
          label={label}
          required={required}
          helperText={helperText}
          margin="normal"
          sx={{ bgcolor: 'grey.50' }}
        />
      )}
    />
  );
}
