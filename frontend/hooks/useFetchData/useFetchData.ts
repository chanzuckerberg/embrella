import { useEffect, useMemo, useState } from "react";
import { getRequestURL } from "@app/common/queries/utils";
import { fetchResource } from "@app/common/queries/fetchResource";
import { API, MOCKED_APIS } from "@app/common/constants/api";

interface UseFetchData<D> {
  data?: D;
  isSuccess: boolean;
}

export const useFetchData = <D>(
  baseURL: string,
  relativeURL: API,
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
    if (MOCKED_APIS[relativeURL] !== undefined) {
      setDataState({
        data: {
          result: MOCKED_APIS[relativeURL],
          pagination: Array.isArray(MOCKED_APIS[relativeURL])
            ? {
                page: 1,
                pageSize: 10,
                totalPages: 1,
                totalResults: MOCKED_APIS[relativeURL].length,
              }
            : undefined,
        } as D,
        isSuccess: true,
      });
      return;
    }
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
  }, [requestURL, shouldFetch, relativeURL]);

  return dataState;
};
