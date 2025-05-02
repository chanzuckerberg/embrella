import { EntityFilterCategories, FiltersList } from "@app/common/types/filter";
import { SearchParam } from "@app/common/types/search";
import { API } from "@app/common/constants/api";
import { useFetchData } from "@hooks/useFetchData/useFetchData";

export const useFetchFilters = <FilterCategory extends EntityFilterCategories>(
  filterlistEndpoint: API,
  searchParam: SearchParam,
): FiltersList<FilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<FilterCategory>>(
    filterlistEndpoint,
    searchParam,
  );

  return filtersData;
};
