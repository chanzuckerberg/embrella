import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useMemo } from 'react';
import { 
  FreezingSessionListResponse, 
  FreezingSession, 
  transformFreezingSession 
} from '@app/common/types/gridLogging/freezingSessionList';

export interface UseFreezingSessionListReturn {
  freezingSessions: FreezingSession[];
  isSuccess: boolean;
  totalCount: number;
  transformedFreezingSessions: ReturnType<typeof transformFreezingSession>[];
  rawData?: FreezingSessionListResponse;
}

export const useFreezingSessionList = (): UseFreezingSessionListReturn => {
  const { data, isSuccess } = useFetchData<FreezingSessionListResponse>(
    API.GRID_LOGGING_FREEZING_SESSIONS
  );

  const freezingSessions = useMemo(() => {
    if (!data) return [];
    return data.results || data.freezing_sessions || [];
  }, [data]);

  const transformedFreezingSessions = useMemo(() => {
    return freezingSessions.map(transformFreezingSession);
  }, [freezingSessions]);

  return {
    freezingSessions,
    isSuccess,
    totalCount: data?.total_freezing_sessions_count || 0,
    transformedFreezingSessions,
    rawData: data,
  };
};