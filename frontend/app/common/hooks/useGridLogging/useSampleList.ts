import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useMemo } from 'react';
import { SampleListResponse, Sample, transformSample } from '@app/common/types/gridLogging/sampleList';

export interface UseSampleListReturn {
  samples: Sample[];
  isSuccess: boolean;
  totalCount: number;
  transformedSamples: ReturnType<typeof transformSample>[];
  rawData?: SampleListResponse;
}

export const useSampleList = (): UseSampleListReturn => {
  const { data, isSuccess } = useFetchData<SampleListResponse>(API.GRID_LOGGING_SAMPLES);

  const samples = useMemo(() => {
    if (!data) return [];
    return data.results || data.samples || [];
  }, [data]);

  const transformedSamples = useMemo(() => {
    return samples.map(transformSample);
  }, [samples]);

  return {
    samples,
    isSuccess,
    totalCount: data?.total_samples_count || 0,
    transformedSamples,
    rawData: data,
  };
};