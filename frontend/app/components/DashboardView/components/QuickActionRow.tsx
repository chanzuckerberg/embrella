'use client';

import { Box } from '@mui/material';
import { Button } from '@czi-sds/components';
import { useRouter } from 'next/navigation';
import { FEATURE_FLAG } from '@app/common/context/FeatureFlagsProvider';

export interface QuickAction {
  label: string;
  href: string;
  icon: React.ReactNode;
  // When set, the action only renders if this flag is enabled for the user.
  featureFlag?: FEATURE_FLAG;
}

// Same predicate MAIN_NAV_ITEMS is filtered by in TopNavigation.
export const visibleActions = (actions: QuickAction[], featureFlags: FEATURE_FLAG[]): QuickAction[] =>
  actions.filter((action) => !action.featureFlag || featureFlags.includes(action.featureFlag));

interface QuickActionRowProps {
  actions: QuickAction[];
  sdsType: 'primary' | 'secondary';
  sdsStyle: 'solid' | 'outline';
}

// A wrapping row of dashboard shortcut buttons. Shared by the default quick
// actions and the demo "Try it Out" examples so both rows stay in step.
export const QuickActionRow = ({ actions, sdsType, sdsStyle }: QuickActionRowProps) => {
  const router = useRouter();

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
      {actions.map((action) => (
        <Button
          key={action.href}
          sdsType={sdsType}
          sdsStyle={sdsStyle}
          startIcon={action.icon}
          onClick={() => router.push(action.href)}
          style={{ flex: '1 1 auto', minWidth: '140px' }}
        >
          {action.label}
        </Button>
      ))}
    </Box>
  );
};
