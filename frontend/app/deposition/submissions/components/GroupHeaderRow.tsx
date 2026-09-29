'use client';

import { Button, Icon } from '@czi-sds/components';
import { Box, IconButton, TableCell, TableRow, Typography } from '@mui/material';

import type { Deposition } from '../../types';
import { COLS } from '../constants';

export function GroupHeaderRow({
  deposition,
  open,
  onToggle,
  onAddDataset,
}: {
  deposition: Deposition;
  open: boolean;
  onToggle: () => void;
  onAddDataset: () => void;
}) {
  const idLabel = deposition.deposition_id ? `cdp-${deposition.deposition_id}` : '(no ID yet)';
  return (
    <TableRow sx={{ bgcolor: 'grey.100' }}>
      <TableCell colSpan={COLS.length} sx={{ py: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton size="small" onClick={onToggle} aria-label={open ? 'Collapse' : 'Expand'}>
            {open ? (
              <Icon sdsIcon="ChevronDown" sdsSize="xs" color="gray" />
            ) : (
              <Icon sdsIcon="ChevronRight" sdsSize="xs" color="gray" />
            )}
          </IconButton>
          <Typography sx={{ fontWeight: 700 }}>Deposition {idLabel}</Typography>
          <Typography color="text.secondary" noWrap sx={{ flex: 1 }}>
            - {deposition.title}
          </Typography>
          {deposition.is_owner && (
            <Button
              sdsType="primary"
              sdsStyle="minimal"
              onClick={onAddDataset}
              size="small"
              startIcon={<Icon sdsIcon="Plus" sdsSize="xs" />}
            >
              Add dataset
            </Button>
          )}
        </Box>
      </TableCell>
    </TableRow>
  );
}
