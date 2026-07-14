'use client';

import { useState } from 'react';
import NextLink from 'next/link';
import { Button } from '@czi-sds/components';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import { Box, Chip, CircularProgress, Link, TableCell, TableRow, Tooltip, Typography } from '@mui/material';

import type { Dataset, DatasetStatus } from '../../types';
import { MAX_SESSION_NAMES, STATUS_META, TYPE_META } from '../constants';
import { absDate, softChipSx, timeAgo } from '../utils';

function statusIcon(status: DatasetStatus) {
  switch (status) {
    case 'draft':
      return <RadioButtonUncheckedIcon sx={{ fontSize: 16, color: 'text.disabled' }} />;
    case 'syncing':
      return <CircularProgress size={13} thickness={5} sx={{ color: 'warning.main' }} />;
    case 'pushed':
      return <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />;
    case 'failed':
      return <ErrorIcon sx={{ fontSize: 16, color: 'error.main' }} />;
  }
}

export function DatasetRow({ dataset }: { dataset: Dataset }) {
  const [showAllSessions, setShowAllSessions] = useState(false);
  const label = dataset.dataset_id ? `ds-${dataset.dataset_id}` : dataset.title || '(untitled draft)';
  const sessionNames = dataset.session_names ?? [];
  const sessionCount = dataset.session_count ?? sessionNames.length;
  const hasMore = sessionNames.length > MAX_SESSION_NAMES;
  const shownNames = showAllSessions ? sessionNames : sessionNames.slice(0, MAX_SESSION_NAMES);
  const meta = STATUS_META[dataset.status];
  const action = dataset.status === 'draft' ? 'Resume' : 'View';
  const typeLabel = dataset.type ?? 'Tomos only';
  const typeColor = TYPE_META[typeLabel] ?? 'default';

  const subtitle = dataset.dataset_id && dataset.title ? dataset.title : '';

  return (
    <TableRow hover sx={{ '& > td': { borderBottom: '1px solid', borderColor: 'divider' } }}>
      <TableCell>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {subtitle}
          </Typography>
        )}
      </TableCell>
      <TableCell>
        {sessionNames.length === 0 ? (
          '-'
        ) : (
          <Box sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
            {shownNames.join(', ')}
            {hasMore && (
              <Link
                component="button"
                type="button"
                variant="body2"
                onClick={() => setShowAllSessions((v) => !v)}
                sx={{ ml: 0.75, verticalAlign: 'baseline' }}
              >
                {showAllSessions ? 'show less' : `+${sessionNames.length - MAX_SESSION_NAMES} more`}
              </Link>
            )}
          </Box>
        )}
        {sessionCount > 0 && (
          <Typography variant="caption" color="text.secondary" display="block">
            ({sessionCount} session{sessionCount === 1 ? '' : 's'})
          </Typography>
        )}
      </TableCell>
      <TableCell>
        <Chip
          size="small"
          variant="outlined"
          label={typeLabel}
          sx={[softChipSx(typeColor), { borderRadius: '4px' }]}
        />
      </TableCell>
      <TableCell>
        <Chip
          size="small"
          variant="outlined"
          icon={statusIcon(dataset.status)}
          label={meta.label}
          sx={softChipSx(meta.color)}
        />
      </TableCell>
      <TableCell sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
        <Tooltip title={absDate(dataset.updated_at)} placement="top">
          <span>{timeAgo(dataset.updated_at)}</span>
        </Tooltip>
      </TableCell>
      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
        <Button
          component={NextLink}
          href={`/deposition/datasets/${dataset.id}`}
          sdsType="secondary"
          sdsStyle="outline"
          size="small"
        >
          {action}
        </Button>
      </TableCell>
    </TableRow>
  );
}
