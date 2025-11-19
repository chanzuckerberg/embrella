// app/common/hooks/useGridLogging/useGridLoggingPucksList.ts
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { PuckListResponse } from '@app/common/types/gridLogging/entities/puckList';
import { API } from '@app/common/constants/api';

export const useGridLoggingPucksList = (caneId?: number) => {
  const searchParams = caneId ? { cane_id: caneId } : {};
  const { data, isSuccess } = useFetchData<PuckListResponse>(API.GRID_LOGGING_PUCKS, searchParams);

  return {
    pucks: data,
    isSuccess,
  };
};

// Hook for fetching pucks filtered by user ID
export const useGridLoggingPucksByUser = (userId?: number) => {
  const searchParams = userId ? { user_id: userId } : {};
  const { data, isSuccess } = useFetchData<PuckListResponse>(API.GRID_LOGGING_PUCKS, searchParams);

  return {
    pucks: data,
    isSuccess,
  };
};

// Hook for fetching pucks filtered by cane ID (alias for useGridLoggingPucksList)
export const useGridLoggingPucksByCane = useGridLoggingPucksList;
