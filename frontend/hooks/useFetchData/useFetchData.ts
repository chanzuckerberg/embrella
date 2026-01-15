import { useEffect, useMemo, useState, useCallback } from 'react';
import { getRequestURL } from '@app/common/queries/utils';
import { fetchResource } from '@app/common/queries/fetchResource';
import { API, DJANGO_URL, MOCKED_APIS } from '@app/common/constants/api';
import { Review } from '@app/components/TomogramViewerView/types';

interface UseFetchData<D> {
  data?: D;
  isSuccess: boolean;
  refetch: () => void;
}

export const useFetchData = <D>(
  relativeURL: string,
  searchParam: Record<string, unknown> = {},
  shouldFetch: boolean = true
): UseFetchData<D> => {
  const [dataState, setDataState] = useState<{ data?: D; isSuccess: boolean }>({
    isSuccess: false,
  });
  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const requestURL = useMemo(() => getRequestURL(DJANGO_URL, relativeURL, searchParam), [relativeURL, searchParam]);

  const refetch = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (!shouldFetch) return;

    (async (): Promise<D> => {
      setDataState((d) => ({
        ...d,
        isSuccess: false,
      }));
      const res = await fetchResource(requestURL);
      // fetchResource handles 401 redirects automatically
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
  }, [requestURL, relativeURL, refetchTrigger, shouldFetch]);

  return { ...dataState, refetch };
};
