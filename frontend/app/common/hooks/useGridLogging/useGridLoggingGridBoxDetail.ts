// app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail.ts
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/gridBoxDetails';
import { API } from '@app/common/constants/api';

export const useGridLoggingGridBoxDetail = (puckId?: number, positionInPuck?: number) => {
  const url = (puckId && positionInPuck) 
    ? API.GRID_LOGGING_PUCK_GRIDBOXINFO
        .replace('puck_id', puckId.toString())
        .replace('position_in_puck', positionInPuck.toString())
    : '';
  
  const { data, isSuccess } = useFetchData<GridBoxDetailResponse>(url);
  
  return {
    gridBoxData: data,
    isSuccess
  };
};