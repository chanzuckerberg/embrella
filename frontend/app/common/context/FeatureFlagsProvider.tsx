'use client';

import { createContext, PropsWithChildren, useContext } from 'react';
import { UserContext } from './UserProvider';

export enum FEATURE_FLAG {
  REVIEW = 'review',
  MANAGE_DATA = 'manage_data',
  DEPOSITION = 'deposition',
  COPICK_WEB = 'copick-web',
  DEMO = 'demo',
}

export const FeatureFlagsContext = createContext<FEATURE_FLAG[]>([]);

export const FeatureFlagsProvider = ({ children }: PropsWithChildren) => {
  // Server-driven flags from /user (global SystemFeatureFlag + per-user overrides).
  const user = useContext(UserContext);
  const flags: FEATURE_FLAG[] = [...new Set((user?.feature_flags ?? []).filter(isFeatureFlag))];

  return <FeatureFlagsContext.Provider value={flags}>{children}</FeatureFlagsContext.Provider>;
};

function isFeatureFlag(value: string | null): value is FEATURE_FLAG {
  return Object.values<string | null>(FEATURE_FLAG).includes(value);
}
