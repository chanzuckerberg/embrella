import { useEffect, useMemo, useState } from "react";
import { getRequestURL } from "@app/common/queries/utils";
import { fetchResource } from "@app/common/queries/fetchResource";

interface UseFetchData<D> {
  data?: D;
  isSuccess: boolean;
}

export const useFetchData = <D>(
  baseURL: string,
  relativeURL: string,
  searchParam: Record<string, unknown> = {},
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
