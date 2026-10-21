import React from 'react';
import { Box } from '@mui/material';

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
