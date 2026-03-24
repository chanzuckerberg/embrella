import React from 'react';
import { Box } from '@mui/material';
import { intervalToDuration } from 'date-fns';

// Utility function for timestamp formatting in History Tab
export const formatTimeAgo = (isoString: string): string => {
  const dur = intervalToDuration({ start: new Date(isoString), end: new Date() });
  const weeks = dur.weeks ?? 0;
  const days = dur.days ?? 0;
  const hours = dur.hours ?? 0;

  if (weeks > 0) {
    return days > 0 ? `${weeks}w ${days}d` : `${weeks}w`;
  }
  if (days > 0) {
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  }
  return `${Math.max(1, hours)}h`;
};

// Props for the TabPanel wrapper that renders content when the active tab matches this panel's index.
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

export const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) =>
  React.createElement(
    'div',
    { role: 'tabpanel', hidden: value !== index },
    value === index ? React.createElement(Box, { sx: { pt: 2 } }, children) : null
  );
