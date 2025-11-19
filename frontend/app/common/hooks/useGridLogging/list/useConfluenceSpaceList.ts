import { API } from '@app/common/constants/api';
import { ConfluenceSpaceListResponse } from '@app/common/types/gridLogging/confluenceSpaceList';
import { useListResource } from '../base/useListResource';

export const useConfluenceSpaceList = () => {
  const { items, isSuccess, totalCount } = useListResource({
    endpoint: API.GRID_LOGGING_CONFLUENCE_SPACES,
    selectItems: (data: ConfluenceSpaceListResponse) => data.spaces || [],
    getTotalCount: (data: ConfluenceSpaceListResponse) => data.total_count || 0,
  });

  return {
    spaces: items,
    isSuccess,
    totalCount,
  };
};