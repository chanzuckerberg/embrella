import { useEffect, useMemo, useState } from 'react';
import { getRequestURL } from '@app/common/queries/utils';
import { fetchResource } from '@app/common/queries/fetchResource';
import { API, DJANGO_URL, MOCKED_APIS } from '@app/common/constants/api';
import { Review } from '@app/components/TomogramViewerView/types';

interface UseFetchData<D> {
  data?: D;
  isSuccess: boolean;
}

export const useFetchData = <D>(relativeURL: string, searchParam: Record<string, unknown> = {}): UseFetchData<D> => {
  const [dataState, setDataState] = useState<UseFetchData<D>>({
    isSuccess: false,
  });
  const requestURL = useMemo(() => getRequestURL(DJANGO_URL, relativeURL, searchParam), [relativeURL, searchParam]);

  useEffect(() => {
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
  }, [requestURL, relativeURL]);

  return dataState;
};
