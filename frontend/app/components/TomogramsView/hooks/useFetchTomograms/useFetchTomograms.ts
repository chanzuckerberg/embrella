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

export const useFetchTomograms = (
  searchParam: SearchParam
): EntityList<TomogramData, "tomograms"> | undefined => {
  const { data: tomogramData } = useFetchData<ApiListResponse<TomogramData>>(
    configs.API_URL,
    API.TOMOGRAMS_V1,
    searchParam
  );
  // TODO: Type is broken because in draft API, the tomograms list is not nested under `result`
  return (
    tomogramData && {
      tomograms: tomogramData,
      pagination: {},
      sortBy: {},
    }
  );
};
