import { ApiListResponse, EntityDataTypes, EntityList } from '@app/common/types/tableState';
import { SearchParam } from '@app/common/types/search';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';

// TODO: May be able to move hook into EntityTable component if it's the only component using this

export const useFetchTableData = <T extends EntityDataTypes>(
  dataEndpoint: API,
  searchParam: SearchParam
): EntityList<T> => {
  const { data, refetch } = useFetchData<ApiListResponse<EntityDataTypes>>(dataEndpoint, searchParam);

  return {
    entities: data?.result,
    pagination: data?.pagination,
    sortBy: data?.sortBy,
    refetch,
  } as EntityList<T>;
};
