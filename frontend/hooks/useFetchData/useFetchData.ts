import { useEffect, useMemo, useState } from "react";
import { fetchResource, getRequestURL } from "@/common/utils";
import { UseFetchData } from "@/hooks/useFetchData/common/types";
import { SearchParam } from "@/common/types";

export const useFetchData = <D>(
  baseURL: string,
  relativeURL: string,
  searchParam: SearchParam = {},
  shouldFetch = true,
): UseFetchData<D> => {
  const [dataState, setDataState] = useState<UseFetchData<D>>({
    isSuccess: false,
  });
  const requestURL = useMemo(
    () => getRequestURL(baseURL, relativeURL, searchParam),
    [baseURL, relativeURL, searchParam],
  );

  useEffect(() => {
    if (!shouldFetch) return;
    (async (): Promise<D> => {
      setDataState((d) => ({
        ...d,
        isSuccess: false,
      }));
      const res = await fetchResource(requestURL);
      if (res.status === 200) {
        return await res.json();
      }
      throw new Error(`Received ${res.status} response`);
    })()
      .then((data) => {
        setDataState({
          data,
          isSuccess: true,
        });
      })
      .catch((err) => {
        console.error(err);
      });
  }, [requestURL, shouldFetch]);

  return dataState;
};
