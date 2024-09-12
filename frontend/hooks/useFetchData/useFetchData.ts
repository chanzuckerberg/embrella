import { useEffect, useMemo, useState } from "react";
import { fetchResource } from "@/common/utils";
import { UseFetchData } from "@/hooks/useFetchData/common/types";

export const useFetchData = <D>(
  requestURLBase: string,
  queryParams?: Record<string, string>,
  shouldFetch = true,
): UseFetchData<D> => {
  const requestURL = getFullUrl(requestURLBase, queryParams);

  const [dataState, setDataState] = useState<UseFetchData<D>>({
    isSuccess: false,
  });

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

function getFullUrl(baseUrl: string, queryParams?: Record<string, string>): string {
  const url = new URL(baseUrl);
  if (queryParams) url.search = new URLSearchParams(queryParams).toString();
  return url.toString();
}
