import { API, DJANGO_URL } from '@app/common/constants/api';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { useState, useEffect } from 'react';

interface FetchError {
  status: number;
  message: string;
}

interface UseFetchMetadataResult {
  data?: MetadataSummaryResponse;
  isSuccess: boolean;
  error?: FetchError;
  isLoading: boolean;
}

export const useFetchMetadataSummary = (
  sessionName: string,
  runNumber: string,
  shouldFetch: boolean = false
): UseFetchMetadataResult => {
  const [data, setData] = useState<MetadataSummaryResponse>();
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<FetchError>();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!shouldFetch) return;

    const fetchData = async () => {
      setIsLoading(true);
      setError(undefined);

      try {
        const response = await fetch(
          `${DJANGO_URL}${API.METADATA_SUMMARY}?session_name=${sessionName}&run_number=${runNumber}`,
          {
            credentials: 'include',
          }
        );

        const responseText = await response.text();

        if (!response.ok) {
          throw {
            status: response.status,
            message: response.statusText,
          };
        }

        let jsonData = null;
        if (responseText) {
          try {
            // Replace NaN with null before parsing
            const cleanedText = responseText.replace(/NaN/g, 'null');
            jsonData = JSON.parse(cleanedText);
          } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw {
              status: 500,
              message: 'Failed to parse server response',
            };
          }
        }

        setData(jsonData);
        setIsSuccess(true);
        setError(undefined);
      } catch (err: unknown) {
        const apiError = err as FetchError;
        setError({
          status: apiError.status || 500,
          message: apiError.message || 'An error occurred while fetching data',
        });
        setIsSuccess(false);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [sessionName, runNumber, shouldFetch]);

  return { data, isSuccess, error, isLoading };
};
