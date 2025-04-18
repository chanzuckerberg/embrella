"use client";

import { createContext, PropsWithChildren, useEffect } from "react";

export enum FEATURE_FLAGS {
  REVIEW = "review",
}

export const FeatureFlagsContext = createContext<FEATURE_FLAGS[]>([]);

export interface FeatureFlagsProviderProps extends PropsWithChildren {
  featureFlagsCookieValue?: string;
}

export const FeatureFlagsProvider = ({
  children,
  featureFlagsCookieValue,
}: FeatureFlagsProviderProps) => {
  useEffect(() => {});

  const enabledFeatureFlags =
    featureFlagsCookieValue
      ?.split(",")
      .filter((flag): flag is FEATURE_FLAGS =>
        Object.values<string>(FEATURE_FLAGS).includes(flag),
      ) ?? [];

  return (
    <FeatureFlagsContext.Provider value={enabledFeatureFlags}>
      {children}
    </FeatureFlagsContext.Provider>
  );
};
