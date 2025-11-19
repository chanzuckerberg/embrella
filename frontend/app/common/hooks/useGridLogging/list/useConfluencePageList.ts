import { API } from '@app/common/constants/api';
import { ConfluencePageListResponse } from '@app/common/types/gridLogging/confluencePageList';
import { useListResource } from '../base/useListResource';

export const useConfluencePageList = () => {
  const { items, isSuccess, totalCount } = useListResource({
    endpoint: API.GRID_LOGGING_CONFLUENCE_PAGES,
    selectItems: (data: ConfluencePageListResponse) => data.pages || [],
    getTotalCount: (data: ConfluencePageListResponse) => data.total_count || 0,
  });

  return {
    pages: items,
    isSuccess,
    totalCount,
  };
};