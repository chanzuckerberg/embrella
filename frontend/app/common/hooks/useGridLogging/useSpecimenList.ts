import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useMemo } from 'react';
import { SpecimenListResponse, Specimen, transformSpecimen } from '@app/common/types/gridLogging/specimenList';

export interface UseSpecimenListReturn {
  specimens: Specimen[];
  isSuccess: boolean;
  totalCount: number;
  transformedSpecimens: ReturnType<typeof transformSpecimen>[];
  rawData?: SpecimenListResponse;
  refetch: () => void;
}

/**
 * Hook to fetch list of all specimens
 * @returns {UseSpecimenListReturn} Specimens data and loading state
 */
export const useSpecimenList = (): UseSpecimenListReturn => {
  const { data, isSuccess, refetch } = useFetchData<SpecimenListResponse>(API.GRID_LOGGING_SPECIMENS);

  const specimens = useMemo(() => {
    if (!data) return [];
    // Handle both paginated and non-paginated responses
    return data.results || data.specimens || [];
  }, [data]);

  const transformedSpecimens = useMemo(() => {
    return specimens.map(transformSpecimen);
  }, [specimens]);

  return {
    specimens,
    isSuccess,
    totalCount: data?.total_specimens_count || 0,
    transformedSpecimens,
    rawData: data,
    refetch,
  };
};