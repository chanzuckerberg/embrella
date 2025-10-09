import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { GridLoggingChoicesResponse } from '@app/common/types/gridLogging/choices';
import { API } from '@app/common/constants/api';

export const useGridLoggingChoices = () => {
  const { data, isSuccess } = useFetchData<GridLoggingChoicesResponse>(API.GRID_LOGGING_CHOICES);

  return {
    choices: data,
    isSuccess,
  };
};