import configs from "@/configs/local";
import { FiltersList, GridFilterCategory, SearchParam } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";

export const useFetchFilters = (
  searchParam: SearchParam,
): FiltersList<GridFilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<GridFilterCategory>>(
    configs.API_URL,
    API.FILTERS_LIST,
    searchParam,
  );

  return filtersData;
};
