import { API } from '@app/common/constants/api';
import { SampleListResponse, Sample, transformSample } from '@app/common/types/gridLogging/sampleList';
import { useListResource } from '../base/useListResource';


export const useSampleList = () => {
  const { items, isSuccess, totalCount, transformedItems, rawData, refetch } = useListResource({
    endpoint: API.GRID_LOGGING_SAMPLES,
    selectItems: (data: SampleListResponse) => data.results || data.samples || [],
    getTotalCount: (data: SampleListResponse) => data.total_samples_count || 0,
    transform: transformSample,
  });

  return {
    samples: items,
    isSuccess,
    totalCount,
    transformedSamples: transformedItems,
    rawData,
    refetch,
  };
};