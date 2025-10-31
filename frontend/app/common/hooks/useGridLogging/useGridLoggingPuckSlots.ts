// app/common/hooks/useGridLogging/useGridLoggingPuckSlots.ts
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { PuckSlotsResponse } from '@app/common/types/gridLogging/puckList';
import { API } from '@app/common/constants/api';

export const useGridLoggingPuckSlots = (puckId?: number) => {
  const url = puckId ? API.GRID_LOGGING_PUCK_SLOTINFO.replace('puck_id', puckId.toString()) : '';
  const { data, isSuccess, refetch } = useFetchData<PuckSlotsResponse>(url);

  return {
    slotsData: data,
    isSuccess,
    refetch,
  };
};
