import configs from "../configs/configs";
import { ApiListResponse, Grid } from "../common/entities";
import { useFetchData } from "./useFetchData";
import { API } from "../common/api";

export const useFetchGrids = (): Grid[] | undefined => {
  const { data: gridsData } = useFetchData<ApiListResponse<Grid>>(
    configs.API_URL + API.GRIDS,
  );
  return gridsData?.Result;
};
