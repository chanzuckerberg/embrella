import configs from "@/configs/local";
import {
  FiltersList,
  GridFilterCategory,
  SearchParam,
} from "@/app/common/types/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/app/common/constants/api";

export const useFetchFilters = (
  searchParam: SearchParam
): FiltersList<GridFilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<GridFilterCategory>>(
    configs.API_URL,
    API.FILTERS_LIST,
    searchParam
  );

  return filtersData;
};
