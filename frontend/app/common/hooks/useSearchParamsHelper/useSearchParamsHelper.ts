import { usePathname, useSearchParams } from "next/navigation";
import { useRouter } from "next/router";
import { useCallback } from "react";

export enum SEARCH_PARAMS {
  // Adding ?enable=yourFlag or ?disable=yourFlag will record your setting in cookies.
  ENABLE_FEATURE_FLAG = "enable",
  DISABLE_FEATURE_FLAG = "disable",
}

export function useSearchParamsHelper() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Helpers to create query strings from current one:
  const getNewSearchStringAdding = useCallback(
    (paramsToAdd: Array<{ key: SEARCH_PARAMS; value: string }>): string => {
      const newSearchParams = new URLSearchParams(searchParams.toString());
      for (const param of paramsToAdd) {
        newSearchParams.set(param.key, param.value);
      }
      return `?${newSearchParams.toString()}`;
    },
    [searchParams],
  );
  const getNewSearchStringRemoving = useCallback(
    (keyToRemove: SEARCH_PARAMS): string => {
      const newSearchParams = new URLSearchParams(searchParams.toString());
      newSearchParams.delete(keyToRemove);
      return `?${newSearchParams.toString()}`;
    },
    [searchParams],
  );

  // Helpers to set router to new query string locations:
  const setSearchParam = useCallback(
    (key: SEARCH_PARAMS, value: string) => {
      router.replace(
        `${pathname}${getNewSearchStringAdding([{ key, value }])}`,
      );
    },
    [pathname, router, getNewSearchStringAdding],
  );
  const deleteSearchParam = useCallback(
    (key: SEARCH_PARAMS) => {
      router.replace(`${pathname}${getNewSearchStringRemoving(key)}`);
    },
    [pathname, router, getNewSearchStringRemoving],
  );

  return {
    getNewSearchStringAdding,
    getNewSearchStringRemoving,
    setSearchParam,
    deleteSearchParam,
  };
}
