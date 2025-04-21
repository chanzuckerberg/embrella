"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { createContext, PropsWithChildren, useEffect } from "react";
import { SEARCH_PARAMS } from "../hooks/useSearchParamsHelper/useSearchParamsHelper";

export enum FEATURE_FLAGS {
  EXAMPLE = "example",
  REVIEW = "review",
}

const ENABLED_FEATURE_FLAGS: FEATURE_FLAGS[] = [FEATURE_FLAGS.EXAMPLE];

export const FeatureFlagsContext = createContext<FEATURE_FLAGS[]>([]);

export interface FeatureFlagsProviderProps extends PropsWithChildren {
  featureFlagsCookieValue?: string;
}

export const FeatureFlagsProvider = ({
  children,
  featureFlagsCookieValue,
}: FeatureFlagsProviderProps) => {
  const cookieValues: string[] = featureFlagsCookieValue?.split(",") ?? [];
  const router = useRouter();
  const searchParams = useSearchParams();

  // Sync cookies with query params.
  useEffect(() => {
    const enableFlag = searchParams.get(SEARCH_PARAMS.ENABLE_FEATURE_FLAG);
    const disableFlag = searchParams.get(SEARCH_PARAMS.DISABLE_FEATURE_FLAG);
    if (enableFlag !== null && !cookieValues.includes(enableFlag)) {
      const newCookieValues = [...cookieValues];
      newCookieValues.push(enableFlag);
      document.cookie = `feature_flags=${newCookieValues.join(",")}; max-age=34560000`;
      router.refresh();
    } else if (disableFlag !== null && cookieValues.includes(disableFlag)) {
      document.cookie = `feature_flags=${cookieValues.filter((flag) => flag !== disableFlag).join(",")}; max-age=34560000`;
      router.refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Only needs to run once.
  }, []);

  return (
    <FeatureFlagsContext.Provider
      value={ENABLED_FEATURE_FLAGS.concat(
        cookieValues.filter((flag): flag is FEATURE_FLAGS =>
          Object.values<string>(FEATURE_FLAGS).includes(flag),
        ),
      )}
    >
      {children}
    </FeatureFlagsContext.Provider>
  );
};
