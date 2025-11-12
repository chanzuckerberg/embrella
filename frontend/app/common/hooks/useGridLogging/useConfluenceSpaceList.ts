import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { ConfluenceSpaceListResponse } from '@app/common/types/gridLogging/confluenceSpaceList';

export const useConfluenceSpaceList = () => {
  const { data, isSuccess } = useFetchData<ConfluenceSpaceListResponse>(
    API.GRID_LOGGING_CONFLUENCE_SPACES
  );

  return {
    spaces: data?.spaces || [],
    isSuccess,
    totalCount: data?.total_count || 0,
  };
};