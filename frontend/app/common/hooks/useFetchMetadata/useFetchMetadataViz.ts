
import configs from "@configs/local";
import { API } from "@app/common/constants/api";
import { useState, useEffect } from "react";
import { MetadataVizResponse } from "@app/common/types/metadataViz/metadataVizData";

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

interface MetadataFilters {
  thickness_pix?: [number, number];
  ctf_resolution_a?: [number, number];
  tilt_axis?: [number, number];
  global_shift_pix?: [number, number];
  bad_patch_low?: [number, number];
  bad_patch_all?: [number, number];
  ctf_score?: [number, number];
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
  filters?: MetadataFilters,
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
        let url = `${configs.API_URL}${API.METADATA_VIZ}?session_name=${sessionName}&run_number=${runNumber}`;
        
        if (filters) {
          const queryFilters = { filters };
          url += `&q=${encodeURIComponent(JSON.stringify(queryFilters))}`;
        }

        const response = await fetch(url);

        if (!response.ok) {
          throw {
            status: response.status,
            message: response.statusText
          };
        }

        const jsonData = await response.json();
        setData(jsonData);
        setIsSuccess(true);
        setError(undefined);
      } catch (err: any) {
        setError({
          status: err.status || 500,
          message: err.message || 'An error occurred while fetching data'
        });
        setIsSuccess(false);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [sessionName, runNumber, filters]);

  return { data, isSuccess, error, isLoading };
};