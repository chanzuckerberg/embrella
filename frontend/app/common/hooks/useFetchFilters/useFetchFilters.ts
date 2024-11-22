import configs from "@/configs/local";

import { FiltersList } from "@app/common/types/filter";
import { SearchParam } from "@app/common/types/search";
import { API } from "@app/common/constants/api";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";

export const useFetchFilters = (
  filterlistEndpoint: API,
  searchParam: SearchParam,
): FiltersList | undefined => {
  const { data: filtersData } = useFetchData<FiltersList>(
    configs.API_URL,
    filterlistEndpoint,
    searchParam,
  );

  return filtersData;
};
