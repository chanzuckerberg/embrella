import { API } from '@app/common/constants/api';
import { UserListResponse } from '@app/common/types/gridLogging/entities/userList';
import { useListResource } from '../base/useListResource';

export const useProjectLeadersList = () => {
  const { rawData, isSuccess } = useListResource({
    endpoint: API.GRID_LOGGING_PROJECT_LEADERS,
    selectItems: (data: UserListResponse) => data.users || [],
    getTotalCount: (data: UserListResponse) => data.total_users_count || 0,
  });

  return {
    projectLeaders: rawData,
    isSuccess,
  };
};