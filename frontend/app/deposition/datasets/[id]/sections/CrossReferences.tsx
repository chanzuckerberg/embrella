'use client';

import { Button } from '@czi-sds/components';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material';

import { SectionCard } from './SectionCard';

export type CrossRefRow = { type: 'publication' | 'related_db'; value: string };

const labelSx = { textTransform: 'uppercase', fontSize: '0.75rem' } as const;

export function CrossReferences({
  crossRefs,
  onAdd,
  onChange,
  onRemove,
  readOnly,
  innerRef,
}: {
  crossRefs: CrossRefRow[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<CrossRefRow>) => void;
  onRemove: (index: number) => void;
  readOnly: boolean;
  innerRef?: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard
      title="Cross references"
      sectionKey="crossrefs"
      innerRef={innerRef ?? (() => {})}
      action={
        !readOnly ? (
          <Button sdsType="primary" sdsStyle="minimal" size="small" startIcon={<AddIcon />} onClick={onAdd}>
            Add entry
          </Button>
        ) : undefined
      }
    >
      {crossRefs.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No cross references added.
        </Typography>
      )}
      {crossRefs.map((r, i) => (
        <Stack key={i} direction="row" spacing={1.5} alignItems="center">
          <TextField
            select
            label="Type"
            value={r.type}
            onChange={(e) => onChange(i, { type: e.target.value as CrossRefRow['type'] })}
            size="small"
            sx={{ minWidth: 190 }}
            disabled={readOnly}
            InputLabelProps={{ sx: labelSx }}
          >
            <MenuItem value="publication">Publication DOI</MenuItem>
            <MenuItem value="related_db">Related DB entry</MenuItem>
          </TextField>
          <TextField
            label="Value"
            value={r.value}
            onChange={(e) => onChange(i, { value: e.target.value })}
            size="small"
            fullWidth
            disabled={readOnly}
            InputLabelProps={{ sx: labelSx }}
          />
          {!readOnly && (
            <Tooltip title="Remove">
              <IconButton aria-label="Remove cross reference" onClick={() => onRemove(i)} size="small">
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ))}
    </SectionCard>
  );
}
