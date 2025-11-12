import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { ConfluencePageListResponse } from '@app/common/types/gridLogging/confluencePageList';

export const useConfluencePageList = () => {
  const { data, isSuccess } = useFetchData<ConfluencePageListResponse>(
    API.GRID_LOGGING_CONFLUENCE_PAGES
  );

  return {
    pages: data?.pages || [],
    isSuccess,
    totalCount: data?.total_count || 0,
  };
};