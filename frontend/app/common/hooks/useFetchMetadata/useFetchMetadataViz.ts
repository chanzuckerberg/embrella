import { API, DJANGO_URL } from '@app/common/constants/api';
import { useState, useEffect } from 'react';
import { MetadataVizResponse, FilterConfig } from '@app/common/types/metadataViz/metadataVizData';

interface FetchError {
  status: number;
  message: string;
}

interface UseFetchMetadataVizResult {
  data?: MetadataVizResponse;
  isSuccess: boolean;
  error?: FetchError;
  isLoading: boolean;
}

export const useFetchMetadataViz = (
  sessionName: string,
  runNumber: string,
  filters?: FilterConfig,
  sortBy?: string,
  sortDirection?: 'asc' | 'desc'
): UseFetchMetadataVizResult => {
  const [data, setData] = useState<MetadataVizResponse>();
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<FetchError>();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(undefined);

      try {
        let url = `${DJANGO_URL}${API.METADATA_VIZ}?session_name=${sessionName}&run_number=${runNumber}`;

        if (filters) {
          url += `&q=${encodeURIComponent(JSON.stringify(filters))}`;
        }

        // Add sorting parameters to the URL if provided
        if (sortBy && sortBy !== 'Select Metric') {
          url += `&sort_by=${encodeURIComponent(sortBy)}`;

          if (sortDirection) {
            url += `&sort_direction=${encodeURIComponent(sortDirection)}`;
          }
        }

        const response = await fetch(url, {
                   credentials: 'include',
               });
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
            // const cleanedText = responseText.replace(/([^"a-zA-Z0-9])NaN([^"a-zA-Z0-9])/g, '$1null$2');
            const cleanedText = responseText.replace(/NaN/g, 'null');
            jsonData = JSON.parse(cleanedText);
          } catch (parseError) {
            console.error('JSON parse error:', parseError);
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
  }, [sessionName, runNumber, filters, sortBy, sortDirection]);

  return { data, isSuccess, error, isLoading };
};
