'use client';

import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

interface BulkActionsBarProps {
  count: number;
  children: React.ReactNode;
}

/**
 * Generic bulk actions bar component that displays the number of selected items
 * and renders custom action buttons as children.
 */
export const BulkActionsBar: React.FC<BulkActionsBarProps> = ({ count, children }) => {
  if (count === 0) {
    return null;
  }

  return (
    <Paper
      sx={{
        p: 2,
        mb: 2,
        backgroundColor: 'primary.light',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <Box display="flex" alignItems="center" gap={2}>
        <Typography variant="body1" fontWeight="bold">
          {count} item{count !== 1 ? 's' : ''} selected
        </Typography>

        {children}
      </Box>
    </Paper>
  );
};
