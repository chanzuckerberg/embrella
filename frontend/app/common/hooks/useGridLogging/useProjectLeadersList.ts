import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { UserListResponse } from '@app/common/types/gridLogging/userList';
import { API } from '@app/common/constants/api';

export const useProjectLeadersList = () => {
  const { data, isSuccess } = useFetchData<UserListResponse>(API.GRID_LOGGING_PROJECT_LEADERS);

  return {
    projectLeaders: data,
    isSuccess,
  };
};