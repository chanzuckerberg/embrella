import { API } from '@app/common/constants/api';
import { FreezingSessionListResponse,transformFreezingSession } from '@app/common/types/gridLogging/entities/freezingSessionList';
import { useListResource } from '../base/useListResource';


export const useFreezingSessionList = () => {
  const { items, isSuccess, totalCount, transformedItems, rawData, refetch } = useListResource({
    endpoint: API.GRID_LOGGING_FREEZING_SESSIONS,
    selectItems: (data: FreezingSessionListResponse) => data.results || data.freezing_sessions || [],
    getTotalCount: (data: FreezingSessionListResponse) => data.total_freezing_sessions_count || 0,
    transform: transformFreezingSession,
  });

  return {
    freezingSessions: items,
    isSuccess,
    totalCount,
    transformedFreezingSessions: transformedItems,
    rawData,
    refetch,
  };
};