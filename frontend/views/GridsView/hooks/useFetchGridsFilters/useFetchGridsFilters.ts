import configs from "@/configs/local";
import { GridFilterCategory } from "@/app/common/types/types";
import { FiltersList } from "@/app/common/types/types";
import { SearchParam } from "@/app/common/types/search";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/app/common/constants/api";

export const useFetchGridsFilters = (
  searchParam: SearchParam
): FiltersList<GridFilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<GridFilterCategory>>(
    configs.API_URL,
    API.FILTERS_LIST,
    searchParam
  );

  return filtersData;
};
