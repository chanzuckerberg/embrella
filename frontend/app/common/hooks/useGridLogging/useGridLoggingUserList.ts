// app/common/hooks/useGridLogging/useGridLoggingUserList.ts
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { userListResponse } from '@app/common/types/gridLogging/userList';
import { API } from '@app/common/constants/api';

export const useGridLoggingUserList = () => {
  const { data, isSuccess } = useFetchData<userListResponse>(API.GRID_LOGGING_USERS);
  
  return {
    users: data,
    isSuccess,
  };
};