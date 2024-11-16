import configs from "@/configs/local";
import { FiltersList, ViewFilterCategory } from "@app/common/types/filter";
import { SearchParam } from "@/app/common/types/search";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/app/common/constants/api";

export const useFetchFilters = (
  filterlistEndpoint: API,
  searchParam: SearchParam
): FiltersList<ViewFilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<ViewFilterCategory>>(
    configs.API_URL,
    filterlistEndpoint,
    searchParam
  );

  return filtersData;
};
