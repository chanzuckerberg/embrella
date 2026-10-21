'use client';

import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { Timeline } from '@app/common/components/Timeline';
import { useGridTimeline } from '@app/common/hooks/timeline/useGridTimeline';

// Scroll inside the tab past this many entries
const MAX_VISIBLE_ENTRIES = 7;

interface HistoryTabProps {
  gridId: number;
}

// Mounted only while the tab is active, so each visit refetches
export const HistoryTab: React.FC<HistoryTabProps> = ({ gridId }) => {
  const { data, isLoading, isError } = useGridTimeline(gridId);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (isError || !data) {
    return (
      <Typography variant="body2" color="error">
        Could not load history.
      </Typography>
    );
  }

  return <Timeline entries={data} maxVisible={MAX_VISIBLE_ENTRIES} />;
};
