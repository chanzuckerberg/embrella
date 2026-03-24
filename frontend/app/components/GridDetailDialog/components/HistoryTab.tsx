'use client';

import React from 'react';
import { Box, Typography } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import { GridDetailsResponse, GridLabelDetail } from '@app/common/types/gridLogging/details/gridDetails';
import { formatTimeAgo } from '../utils';

interface HistoryTabProps {
  gridDetails: GridDetailsResponse;
}

export const HistoryTab: React.FC<HistoryTabProps> = ({ gridDetails }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
    <Typography variant="body2" color="text.secondary">
      Created: {gridDetails.created_on || '-'} · Last Updated: {gridDetails.updated_on || '-'}
    </Typography>

    <Typography variant="subtitle2" sx={{ mt: 1 }}>
      Label History
    </Typography>
    {gridDetails.labels.length === 0 ? (
      <Typography variant="body2" color="text.secondary">
        No labels added yet.
      </Typography>
    ) : (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {gridDetails.labels.map((label: GridLabelDetail) => (
          <Box
            key={`${label.id}-${label.added_at}`}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              p: 1,
              borderRadius: 1,
              bgcolor: 'rgba(0,0,0,0.02)',
            }}
          >
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                backgroundColor: label.color,
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 80 }}>
              {label.name}
            </Typography>
            {label.added_by !== null && label.added_by !== '' && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                by {label.added_by}
              </Typography>
            )}
            {!!label.added_at && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 1 }}>
                <AccessTimeIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary">
                  {formatTimeAgo(label.added_at)}
                </Typography>
              </Box>
            )}
          </Box>
        ))}
      </Box>
    )}
  </Box>
);
