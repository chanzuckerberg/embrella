import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { GridDetailsResponse } from '@app/common/types/gridLogging/details/gridDetails';
import { API } from '@app/common/constants/api';

export const useGridDetails = (gridId: number | null) => {
  const url = gridId ? API.GRID_DETAIL.replace('grid_id', gridId.toString()) : '';

  const { data, isSuccess, refetch } = useFetchData<GridDetailsResponse>(url);

  return {
    gridDetails: data,
    isSuccess,
    refetch,
  };
};
