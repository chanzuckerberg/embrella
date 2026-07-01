'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { createContext, PropsWithChildren, useContext, useEffect } from 'react';
import { SEARCH_PARAM_NAME } from '../types/search';
import { COOKIE_NAME } from '../types/cookies';
import { UserContext } from './UserProvider';

export enum FEATURE_FLAG {
  EXAMPLE = 'example',
  REVIEW = 'review',
  MANAGE_DATA = 'manage_data',
  DEPOSITION = 'deposition',
}

const LAUNCHED_FEATURE_FLAGS: FEATURE_FLAG[] = [FEATURE_FLAG.EXAMPLE, FEATURE_FLAG.REVIEW];

export const FeatureFlagsContext = createContext<FEATURE_FLAG[]>([]);

export interface FeatureFlagsProviderProps extends PropsWithChildren {
  featureFlagsCookie?: string;
}

export const FeatureFlagsProvider = ({ children, featureFlagsCookie }: FeatureFlagsProviderProps) => {
  const manuallyEnabledFlags: FEATURE_FLAG[] = featureFlagsCookie?.split(',').filter(isFeatureFlag) ?? [];

  // Server-driven flags from /user (global SystemFeatureFlag + per-user overrides).
  const user = useContext(UserContext);
  const serverFlags: FEATURE_FLAG[] = (user?.feature_flags ?? []).filter(isFeatureFlag);

  const router = useRouter();
  const searchParams = useSearchParams();

  // Sync manually enabled flags in cookies with query params.
  useEffect(() => {
    const enableFlag = searchParams.get(SEARCH_PARAM_NAME.ENABLE_FEATURE_FLAG);
    const disableFlag = searchParams.get(SEARCH_PARAM_NAME.DISABLE_FEATURE_FLAG);
    if (isFeatureFlag(enableFlag) && !manuallyEnabledFlags.includes(enableFlag)) {
      document.cookie = `${COOKIE_NAME.FEATURE_FLAGS}=${[...manuallyEnabledFlags, enableFlag].join(',')}; path=/; max-age=34560000`;
      router.refresh();
    } else if (isFeatureFlag(disableFlag) && manuallyEnabledFlags.includes(disableFlag)) {
      document.cookie = `${COOKIE_NAME.FEATURE_FLAGS}=${manuallyEnabledFlags.filter((flag) => flag !== disableFlag).join(',')}; path=/; max-age=34560000`;
      router.refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Only needs to run once.
  }, []);

  return (
    <FeatureFlagsContext.Provider
      value={[...new Set([...LAUNCHED_FEATURE_FLAGS, ...manuallyEnabledFlags, ...serverFlags])]}
    >
      {children}
    </FeatureFlagsContext.Provider>
  );
};

function isFeatureFlag(value: string | null): value is FEATURE_FLAG {
  return Object.values<string | null>(FEATURE_FLAG).includes(value);
}
