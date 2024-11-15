import configs from "@/configs/local";
import { ApiListResponse, EntityList } from "@/app/common/types/types";
import { SearchParam } from "@/app/common/types/search";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/app/common/constants/api";
import { TomogramData } from "@/app/common/types/tomogram";

// TODO: replace TomogramList with EntityList<TomogramData, "tomograms"> when filtering is implemented
export type TomogramList = {
  [entityName in "tomograms"]: TomogramData[];
};

export const useFetchTableData = <DataType, DataResponseField extends string>(
  dataEndpoint: API,
  searchParam: SearchParam,
  dataResponseField: DataResponseField
): EntityList<TomogramData, DataResponseField> | undefined => {
  const { data: tomogramData } = useFetchData<ApiListResponse<DataType>>(
    configs.API_URL,
    dataEndpoint,
    searchParam
  );
  // TODO: Type is broken because in draft API, the tomograms list is not nested under `result`
  return (
    tomogramData && {
      [dataResponseField]: tomogramData,
      pagination: {},
      sortBy: {},
    }
  );
};
