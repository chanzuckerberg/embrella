import configs from "@/configs/local";
import { ApiListResponse, GridData } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";
import { UseFetchGridsOptions } from "@/views/GridsView/hooks/common/types";

export const useFetchGrids = (options: UseFetchGridsOptions = {}): GridData[] | undefined => {
  const queryParams: Record<string, string> = {};
  if (options.sort) {
    queryParams.sort = options.sort.column;
    queryParams.asc = options.sort.ascending ? "true" : "false";
  }
  const { data: gridsData } = useFetchData<ApiListResponse<GridData>>(
    configs.API_URL + API.GRIDS,
    queryParams
  );
  return gridsData?.result;
};
