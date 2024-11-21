import configs from "@/configs/local";
import { GridData } from "@app/common/types/types";
import { ApiListResponse, EntityList } from "@app/common/types/tableState";
import { SearchParam } from "@app/common/types/search";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@app/common/constants/api";
import { TomogramData } from "@app/common/types/tomogram";

type APIResponseFieldMap = {
  tomograms: TomogramData;
  grids: GridData;
};

export const useFetchTableData = <K extends keyof APIResponseFieldMap>(
  dataEndpoint: API,
  searchParam: SearchParam,
  dataResponseField: K
): EntityList<APIResponseFieldMap[K], K> | undefined => {
  const { data } = useFetchData<ApiListResponse<APIResponseFieldMap[K]>>(
    configs.API_URL,
    dataEndpoint,
    searchParam
  );
  return (
    data &&
    ({
      [dataResponseField]: data.result,
      pagination: data.pagination,
      sortBy: data.sortBy,
    } as EntityList<APIResponseFieldMap[K], K>)
  );
};
