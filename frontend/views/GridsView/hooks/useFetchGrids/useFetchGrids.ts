import configs from "@/configs/local";
import {
  ApiListResponse,
  EntityList,
  GridData,
} from "@/app/common/types/types";
import { SearchParam } from "@/app/common/types/search";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/app/common/constants/api";

export const useFetchGrids = (
  searchParam: SearchParam
): EntityList<GridData, "grids"> | undefined => {
  const { data: gridsData } = useFetchData<ApiListResponse<GridData>>(
    configs.API_URL,
    API.GRIDS,
    searchParam
  );
  return (
    gridsData && {
      grids: gridsData.result,
      pagination: gridsData.pagination,
      sortBy: gridsData.sortBy,
    }
  );
};
