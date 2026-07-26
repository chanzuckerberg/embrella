'use client';

import { useContext } from 'react';
import { Box, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { ViewModule as GridExampleIcon, Summarize as SummaryIcon, Visibility as ViewerIcon } from '@mui/icons-material';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { QuickAction, QuickActionRow, visibleActions } from '../QuickActionRow';

// Deep links straight into the seeded demo data (see
// umbrella/scripts/populate_demo.py), so a first-time visitor lands on a
// populated page instead of an empty table. Read-only, no cluster needed.
const TRY_IT_OUT_ACTIONS: QuickAction[] = [
  {
    label: 'Grid Example',
    href: '/samples/cryo_grids?gridDetail=1',
    icon: <GridExampleIcon />,
    featureFlag: FEATURE_FLAG.DEMO,
  },
  {
    label: 'Summary Example',
    href: '/metadata/view/26feb20d/run002',
    icon: <SummaryIcon />,
    featureFlag: FEATURE_FLAG.DEMO,
  },
  {
    label: 'Viewer Example',
    href: '/processing/tomograms/reviews/cfbe4c73-683d-453e-982e-6442abf2802b',
    icon: <ViewerIcon />,
    featureFlag: FEATURE_FLAG.DEMO,
  },
];

export const DemoQuickLinks = () => {
  const featureFlags = useContext(FeatureFlagsContext);
  const actions = visibleActions(TRY_IT_OUT_ACTIONS, featureFlags);

  if (actions.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        p: 2.5,
        mb: 4,
        borderRadius: 1,
        border: 1,
        borderColor: (t) => alpha(t.palette.info.main, 0.3),
        bgcolor: (t) => alpha(t.palette.info.main, 0.06),
      }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
        Try it Out
      </Typography>
      <QuickActionRow actions={actions} sdsType="secondary" sdsStyle="outline" />
    </Box>
  );
};
