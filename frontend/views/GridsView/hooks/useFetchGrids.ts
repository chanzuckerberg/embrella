import configs from "@/configs/configs";
import { ApiListResponse, GridData } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";

export const useFetchGrids = (): GridData[] | undefined => {
  const { data: gridsData } = useFetchData<ApiListResponse<GridData>>(
    configs.API_URL + API.GRIDS,
  );
  return gridsData?.result;
};
