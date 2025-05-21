import { useEffect, useMemo, useState } from 'react';
import { getRequestURL } from '@app/common/queries/utils';
import { fetchResource } from '@app/common/queries/fetchResource';
import { API, DJANGO_URL, MOCKED_APIS } from '@app/common/constants/api';
import { Review } from '@app/components/TomogramViewerView/types';

interface UseFetchData<D> {
  data?: D;
  isSuccess: boolean;
}

export const useFetchData = <D>(relativeURL: API, searchParam: Record<string, unknown> = {}): UseFetchData<D> => {
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

interface UseFetchReviewData {
  data: Review | undefined;
  isSuccess: boolean;
  isLoading: boolean;
}

export const useFetchReviewData = (reviewId: string): UseFetchReviewData => {
  const [dataState, setDataState] = useState<UseFetchReviewData>({
    data: undefined,
    isSuccess: false,
    isLoading: true,
  });
  useEffect(() => {
    const fetchData = async () => {
      setDataState((prev) => ({ ...prev, isLoading: true }));

      const mockResponse = MOCKED_APIS[API.REVIEW](`${DJANGO_URL}/api/reviews/${reviewId}`);
      if (mockResponse !== undefined) {
        setDataState({
          data: mockResponse,
          isSuccess: true,
          isLoading: false,
        });
        return;
      }

      setDataState((prev) => ({ ...prev, isLoading: false }));
    };

    fetchData();
  }, [reviewId]);

  return dataState;
};
