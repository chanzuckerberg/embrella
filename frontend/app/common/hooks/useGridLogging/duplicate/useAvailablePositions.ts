import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { AvailablePositionsResponse } from '@app/common/types/gridLogging/entities/grid';

export const useAvailablePositions = (boxId?: number | null) => {
  const url = boxId ? API.GRID_BOX_AVAILABLE_POSITIONS : '';
  const { data, isSuccess, refetch } = useFetchData<AvailablePositionsResponse>(url, boxId ? { box_id: boxId } : {});
  return {
    availablePositions: data,
    isSuccess,
    refetch,
  };
};
