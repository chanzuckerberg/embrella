import { API } from '@app/common/constants/api';
import { SpecimenListResponse, transformSpecimen } from '@app/common/types/gridLogging/specimenList';
import { useListResource } from '../base/useListResource';

export const useSpecimenList = () => {
  const { items, isSuccess, totalCount, transformedItems, rawData, refetch } = useListResource({
    endpoint: API.GRID_LOGGING_SPECIMENS,
    selectItems: (data: SpecimenListResponse) => data.results || data.specimens || [],
    getTotalCount: (data: SpecimenListResponse) => data.total_specimens_count || 0,
    transform: transformSpecimen,
  });

  return {
    specimens: items,
    isSuccess,
    totalCount,
    transformedSpecimens: transformedItems,
    rawData,
    refetch,
  };
};