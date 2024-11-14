import { FilterConfig } from "@/app/components/Filter/common/types";
import { FiltersList } from "@/app/common/types/filter";
import { UseFilterList } from "@/app/components/Filter/hooks/useFilterList/types";
import { buildFilterGroups } from "@/app/components/Filter/hooks/useFilterList/utils";
import { useMemo } from "react";

export const useFilterList = <FilterId, FilterCategory extends string>(
  config: FilterConfig<FilterId, FilterCategory>[][],
  filtersList?: FiltersList<FilterCategory>
): UseFilterList<FilterId, FilterCategory> => {
  return useMemo(
    () => buildFilterGroups(config, filtersList?.filters),
    [config, filtersList]
  );
};
