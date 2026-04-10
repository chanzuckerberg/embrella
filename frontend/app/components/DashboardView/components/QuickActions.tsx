'use client';

import { Box } from '@mui/material';
import { Button } from '@czi-sds/components';
import { useRouter } from 'next/navigation';
import {
  RocketLaunch as LaunchIcon,
  Science as SessionIcon,
  GridOn as GridIcon,
  List as ListIcon,
} from '@mui/icons-material';

interface QuickAction {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const QUICK_ACTIONS: QuickAction[] = [
  { label: 'Launch Job', href: '/processing/jobs/launch', icon: <LaunchIcon /> },
  { label: 'New Session', href: '/sessions/new/tem', icon: <SessionIcon /> },
  { label: 'Grid Logging', href: '/samples/grid_logging', icon: <GridIcon /> },
  { label: 'Grid Inventory', href: '/samples/cryo_grids', icon: <ListIcon /> },
];

export const QuickActions = () => {
  const router = useRouter();

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 2, pb: 5 }}>
        {QUICK_ACTIONS.map((action) => (
          <Button
            key={action.href}
            sdsType="primary"
            sdsStyle="rounded"
            startIcon={action.icon}
            onClick={() => router.push(action.href)}
            style={{ flex: 1 }}
          >
            {action.label}
          </Button>
        ))}
      </Box>
    </Box>
  );
};
