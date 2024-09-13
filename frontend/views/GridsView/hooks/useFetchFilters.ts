import configs from "@/configs/local";
import { FiltersList, GridFilterCategory } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";
import { getRequestURL } from "@/common/utils";
import { DEFAULT_FILTER_PARAM } from "@/views/GridsView/hooks/useGridList/constants";

export const useFetchFilters = ():
  | FiltersList<GridFilterCategory>
  | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<GridFilterCategory>>(
    getRequestURL(configs.API_URL, API.FILTERS_LIST, [
      { name: "q", value: DEFAULT_FILTER_PARAM },
    ]),
  );

  return filtersData;
};
