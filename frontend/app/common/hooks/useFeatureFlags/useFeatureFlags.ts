import { useSearchParams } from "next/navigation";
import {
  SEARCH_PARAMS,
  useSearchParamsHelper,
} from "../useSearchParamsHelper/useSearchParamsHelper";
import { useEffect } from "react";

const FEATURE_FLAG_LAUNCHES: Partial<Record<SEARCH_PARAMS, boolean>> = {
  [SEARCH_PARAMS.REVIEW]: false,
};

export const useFeatureFlag = (
  featureFlag: keyof typeof FEATURE_FLAG_LAUNCHES,
): boolean => {
  const { deleteSearchParam } = useSearchParamsHelper();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (FEATURE_FLAG_LAUNCHES[featureFlag]) {
      deleteSearchParam(featureFlag);
    }
  });

  return true;
  if (searchParams.get(featureFlag) === "true") {
    localStorage;
  }
  return FEATURE_FLAG_LAUNCHES[featureFlag] || searchParams.has(featureFlag);
};
