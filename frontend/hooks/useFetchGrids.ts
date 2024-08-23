import configs from "../configs/configs";
import { Grid } from "../common/entities";
import { useFetchData } from "./useFetchData";
import { API } from "../common/api";

export const useFetchGrids = (): Grid[] | undefined => {
  const { data: grids } = useFetchData<Grid[]>(configs.API_URL + API.GRIDS);
  return grids;
};
