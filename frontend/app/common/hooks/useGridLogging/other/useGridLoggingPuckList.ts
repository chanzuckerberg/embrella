// app/common/hooks/useGridLogging/useGridLoggingPucksList.ts
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { PuckListResponse } from '@app/common/types/gridLogging/entities/puckList';
import { API } from '@app/common/constants/api';

export const useGridLoggingPucksList = (caneId?: number) => {
  const searchParams = caneId ? { cane_id: caneId } : {};
  const { data, isSuccess, refetch } = useFetchData<PuckListResponse>(API.GRID_LOGGING_PUCKS, searchParams);

  return {
    pucks: data,
    isSuccess,
    refetch,
  };
};

// Hook for fetching pucks filtered by user ID
export const useGridLoggingPucksByUser = (userId?: number) => {
  const searchParams = userId ? { user_id: userId } : {};
  const { data, isSuccess, refetch } = useFetchData<PuckListResponse>(API.GRID_LOGGING_PUCKS, searchParams);

  return {
    pucks: data,
    isSuccess,
    refetch,
  };
};

// Pucks holding at least one of the user's grids, whoever owns the puck; skipped without a user.
export const useGridLoggingPucksByGridOwner = (userId?: number) => {
  const searchParams = userId ? { grid_owner_id: userId } : {};
  const { data, isSuccess } = useFetchData<PuckListResponse>(API.GRID_LOGGING_PUCKS, searchParams, Boolean(userId));

  return {
    pucks: data,
    isSuccess,
  };
};

// Hook for fetching pucks filtered by cane ID (alias for useGridLoggingPucksList)
export const useGridLoggingPucksByCane = useGridLoggingPucksList;
