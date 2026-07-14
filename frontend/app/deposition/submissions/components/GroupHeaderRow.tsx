'use client';

import { Button } from '@czi-sds/components';
import AddIcon from '@mui/icons-material/Add';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
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
            {open ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
          </IconButton>
          <Typography sx={{ fontWeight: 700 }}>Deposition {idLabel}</Typography>
          <Typography color="text.secondary" noWrap sx={{ flex: 1 }}>
            — {deposition.title}
          </Typography>
          <Button sdsType="primary" sdsStyle="minimal" onClick={onAddDataset} startIcon={<AddIcon fontSize="small" />}>
            Add dataset
          </Button>
        </Box>
      </TableCell>
    </TableRow>
  );
}
