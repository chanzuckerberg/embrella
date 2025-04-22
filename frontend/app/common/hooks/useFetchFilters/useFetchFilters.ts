import configs from "@configs/local";

import { EntityFilterCategories, FiltersList } from "@app/common/types/filter";
import { SearchParam } from "@app/common/types/search";
import { GET_API } from "@app/common/constants/api";
import { useFetchData } from "@hooks/useFetchData/useFetchData";

export const useFetchFilters = <FilterCategory extends EntityFilterCategories>(
  filterlistEndpoint: GET_API,
  searchParam: SearchParam,
): FiltersList<FilterCategory> | undefined => {
  const { data: filtersData } = useFetchData<FiltersList<FilterCategory>>(
    configs.API_URL,
    filterlistEndpoint,
    searchParam,
  );

  return filtersData;
};
