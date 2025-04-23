// import configs from "@configs/local";
// import { API } from "@app/common/constants/api";
// import { useFetchData } from "@hooks/useFetchData/useFetchData";
// import { MetadataSummaryResponse } from "@app/common/types/metadataViz/metadataSummary";

// interface FetchError {
//   status: number;
//   message: string;
// }

// export const useFetchMetadataSummary = (
//   sessionName: string,
//   runNumber: string,
//   shouldFetch: boolean = false,
// ): {
//   data?: MetadataSummaryResponse;
//   isSuccess: boolean;
//   error?: FetchError;
// } => {
//   // Use simple query parameters
//   const searchParam = {
//     session_name: sessionName,
//     run_number: runNumber,
//     enabled: shouldFetch
//   };

//   return useFetchData<MetadataSummaryResponse>(
//     configs.API_URL,
//     API.METADATA_SUMMARY,
//     searchParam
//   );
// };

import configs from "@configs/local";
import { API } from "@app/common/constants/api";
import { MetadataSummaryResponse } from "@app/common/types/metadataViz/metadataSummary";
import { useState, useEffect } from "react";

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
  shouldFetch: boolean = false,
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
          `${configs.API_URL}${API.METADATA_SUMMARY}?session_name=${sessionName}&run_number=${runNumber}`
        );

        if (!response.ok) {
          throw {
            status: response.status,
            message: response.status === 404 
              ? 'Required files not found. Please check if the session and run number are correct.'
              : `Error: ${response.statusText}`
          };
        }

        const jsonData = await response.json();
        setData(jsonData);
        setIsSuccess(true);
        setError(undefined);
      } catch (err: any) {
        console.error('Error fetching metadata:', err);
        setError({
          status: err.status || 500,
          message: err.message || 'An error occurred while fetching metadata'
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