'use client';

import { useEffect, useState } from 'react';
import { Autocomplete, Chip, TextField, Box, Typography, SxProps, Theme } from '@mui/material';
import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';

interface LabelsAutocompleteProps {
  /** Current labels on the grid (controlled) */
  value: LabelData[];
  /** Called with the new labels array after every add/remove */
  onChange: (labels: LabelData[]) => void;
  /** When true, applies disabled visual styling and hides delete icons */
  disabled?: boolean;
  /** Extra sx passed to the Autocomplete root */
  sx?: SxProps<Theme>;
}

export const LabelsAutocomplete: React.FC<LabelsAutocompleteProps> = ({ value, onChange, disabled = false, sx }) => {
  const [allLabels, setAllLabels] = useState<LabelData[]>([]);

  useEffect(() => {
    fetch(`${DJANGO_URL}${API.LABELS}`, { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setAllLabels(Array.isArray(data) ? data : (data.results ?? [])))
      .catch(() => setAllLabels([]));
  }, []);

  const handleChange = async (_event: React.SyntheticEvent, newValue: (LabelData | string)[]) => {
    const resolved: LabelData[] = [];
    for (const item of newValue) {
      if (typeof item === 'string') {
        const trimmed = item.trim();
        if (!trimmed) continue;
        const existing = allLabels.find((l) => l.name.toLowerCase() === trimmed.toLowerCase());
        if (existing) {
          resolved.push(existing);
        } else {
          try {
            const res = await fetch(`${DJANGO_URL}${POST_API.CREATE_LABEL}`, {
              method: 'POST',
              credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: trimmed }),
            });
            if (res.ok) {
              const label: LabelData = await res.json();
              setAllLabels((prev) => [...prev, label]);
              resolved.push(label);
            }
          } catch (e) {
            console.error('Failed to create label:', e);
          }
        }
      } else {
        resolved.push(item);
      }
    }
    onChange(resolved);
  };

  return (
    <Autocomplete
      multiple
      freeSolo
      disabled={disabled}
      options={allLabels.filter((l) => !value.some((v) => v.id === l.id))}
      value={value}
      getOptionLabel={(option) => (typeof option === 'string' ? option : option.name)}
      isOptionEqualToValue={(option, val) => option.id === val.id}
      onChange={handleChange}
      renderTags={(tagValue, getTagProps) =>
        tagValue.map((label, index) => {
          const { onDelete, ...tagProps } = getTagProps({ index });
          return (
            <Chip
              {...tagProps}
              {...(!disabled ? { onDelete } : {})}
              key={label.id}
              label={label.name}
              size="small"
              sx={{
                backgroundColor: `${label.color} !important`,
                color: '#fff',
                fontWeight: 500,
                height: 22,
                fontSize: 12,
                borderRadius: '4px',
                opacity: '1 !important',
                '& .MuiChip-label': { px: '6px' },
                '& .MuiChip-deleteIcon': {
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: 16,
                  '&:hover': { color: '#fff' },
                },
              }}
            />
          );
        })
      }
      renderOption={(props, option) => (
        <li {...props} key={option.id}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: option.color,
              flexShrink: 0,
              mr: 1,
            }}
          />
          <Typography variant="body2">{option.name}</Typography>
        </li>
      )}
      renderInput={(params) => <TextField {...params} label="Labels" />}
      ListboxProps={{ sx: { maxHeight: 200 } }}
      sx={sx}
    />
  );
};
