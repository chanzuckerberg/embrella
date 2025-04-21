"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { createContext, PropsWithChildren, useEffect } from "react";
import { SEARCH_PARAMS } from "../hooks/useSearchParamsHelper/useSearchParamsHelper";

export enum FEATURE_FLAG {
  EXAMPLE = "example",
  REVIEW = "review",
}

const LAUNCHED_FEATURE_FLAGS: FEATURE_FLAG[] = [FEATURE_FLAG.EXAMPLE];

export const FeatureFlagsContext = createContext<FEATURE_FLAG[]>([]);

export interface FeatureFlagsProviderProps extends PropsWithChildren {
  featureFlagsCookie?: string;
}

export const FeatureFlagsProvider = ({
  children,
  featureFlagsCookie,
}: FeatureFlagsProviderProps) => {
  const manuallyEnabledFlags: FEATURE_FLAG[] =
    featureFlagsCookie?.split(",").filter(isFeatureFlag) ?? [];

  const router = useRouter();
  const searchParams = useSearchParams();

  // Sync manually enabled flags in cookies with query params.
  useEffect(() => {
    const enableFlag = searchParams.get(SEARCH_PARAMS.ENABLE_FEATURE_FLAG);
    const disableFlag = searchParams.get(SEARCH_PARAMS.DISABLE_FEATURE_FLAG);
    if (
      isFeatureFlag(enableFlag) &&
      !manuallyEnabledFlags.includes(enableFlag)
    ) {
      document.cookie = `feature_flags=${[...manuallyEnabledFlags, enableFlag].join(",")}; max-age=34560000`;
      router.refresh();
    } else if (
      isFeatureFlag(disableFlag) &&
      manuallyEnabledFlags.includes(disableFlag)
    ) {
      document.cookie = `feature_flags=${manuallyEnabledFlags.filter((flag) => flag !== disableFlag).join(",")}; max-age=34560000`;
      router.refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Only needs to run once.
  }, []);

  return (
    <FeatureFlagsContext.Provider
      value={LAUNCHED_FEATURE_FLAGS.concat(manuallyEnabledFlags)}
    >
      {children}
    </FeatureFlagsContext.Provider>
  );
};

function isFeatureFlag(value: string | null): value is FEATURE_FLAG {
  return Object.values<string | null>(FEATURE_FLAG).includes(value);
}
