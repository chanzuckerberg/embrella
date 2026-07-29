'use client';

import { Button, Icon } from '@czi-sds/components';
import { IconButton, Stack, TextField, Tooltip, Typography } from '@mui/material';

import type { DatasetFunding } from '../../../types';
import { SectionCard } from './SectionCard';

const labelSx = { textTransform: 'uppercase', fontSize: '0.75rem' } as const;

export function Funding({
  funding,
  onAdd,
  onChange,
  onRemove,
  readOnly,
  innerRef,
}: {
  funding: DatasetFunding[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<DatasetFunding>) => void;
  onRemove: (index: number) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard
      title="Funding"
      sectionKey="funding"
      innerRef={innerRef}
      action={
        !readOnly ? (
          <Button
            sdsType="primary"
            sdsStyle="minimal"
            size="small"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={onAdd}
          >
            Add
          </Button>
        ) : undefined
      }
    >
      {funding.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No funding sources added.
        </Typography>
      )}
      {funding.map((f, i) => (
        <Stack key={i} direction="row" spacing={1.5} alignItems="center">
          <TextField
            label="Agency"
            value={f.funding_agency_name}
            onChange={(e) => onChange(i, { funding_agency_name: e.target.value })}
            size="small"
            fullWidth
            disabled={readOnly}
            InputLabelProps={{ sx: labelSx }}
          />
          <TextField
            label="Grant ID"
            value={f.grant_id ?? ''}
            onChange={(e) => onChange(i, { grant_id: e.target.value })}
            size="small"
            fullWidth
            disabled={readOnly}
            InputLabelProps={{ sx: labelSx }}
          />
          {!readOnly && (
            <Tooltip title="Remove">
              <IconButton aria-label="Remove funding" onClick={() => onRemove(i)} size="small">
                <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ))}
    </SectionCard>
  );
}
