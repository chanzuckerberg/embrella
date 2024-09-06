import configs from "@/configs/local";
import { FiltersList } from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";

export const useFetchFilters = (): FiltersList | undefined => {
  const { data: filtersData } = useFetchData<FiltersList>(
    configs.API_URL + API.FILTERS_LIST,
  );
  return filtersData;
};
