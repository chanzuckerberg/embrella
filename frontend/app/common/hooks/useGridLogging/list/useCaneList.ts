import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';

export interface Cane {
  id: number;
  name: string;
  color: string;
  color_code: string;
  position_in_dewar: number;
  max_pucks: number;
  dewar: number;
  pucks_count: number;
}

export interface CaneListResponse {
  canes: Cane[];
}

export const useGridLoggingCaneList = () => {
  const { data, isSuccess } = useFetchData<CaneListResponse>(API.GRID_LOGGING_CANES);

  return {
    canes: data?.canes || [],
    isSuccess,
  };
};
