import configs from "@/configs/local";
import { FiltersList, GridFilterCategory, SearchParam } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";
import { DEFAULT_FILTER_SEARCH_PARAM } from "@/views/GridsView/hooks/useFetchFilters/constants";

export const useFetchFilters = (
  searchParam: SearchParam, // filter related search param "q".
): FiltersList<GridFilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<GridFilterCategory>>(
    configs.API_URL,
    API.FILTERS_LIST,
    { ...DEFAULT_FILTER_SEARCH_PARAM, ...searchParam },
  );

  return filtersData;
};
