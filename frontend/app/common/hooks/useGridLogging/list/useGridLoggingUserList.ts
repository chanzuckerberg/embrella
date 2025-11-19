import { API } from '@app/common/constants/api';
import { UserListResponse } from '@app/common/types/gridLogging/userList';
import { useListResource } from '../base/useListResource';

export const useGridLoggingUserList = () => {
  const { rawData, isSuccess } = useListResource({
    endpoint: API.GRID_LOGGING_USERS,
    selectItems: (data: UserListResponse) => data.users || [],
    getTotalCount: (data: UserListResponse) => data.total_users_count || 0,
  });

  return {
    users: rawData,
    isSuccess,
  };
};