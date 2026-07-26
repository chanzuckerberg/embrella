'use client';

import { Box } from '@mui/material';
import {
  RocketLaunch as LaunchIcon,
  Science as SessionIcon,
  GridOn as GridIcon,
  List as ListIcon,
} from '@mui/icons-material';
import { QuickAction, QuickActionRow } from './QuickActionRow';

const QUICK_ACTIONS: QuickAction[] = [
  { label: 'Grid Inventory', href: '/samples/cryo_grids', icon: <ListIcon /> },
  { label: 'Grid Logging', href: '/samples/grid_logging', icon: <GridIcon /> },
  { label: 'New Session', href: '/sessions/new/tem', icon: <SessionIcon /> },
  { label: 'Launch Job', href: '/processing/jobs/launch', icon: <LaunchIcon /> },
];

export const QuickActions = () => (
  <Box sx={{ pb: 5 }}>
    <QuickActionRow actions={QUICK_ACTIONS} sdsType="primary" sdsStyle="solid" />
  </Box>
);
