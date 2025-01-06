import { FilterConfig } from "@app/common/types/filter";
import { UseFilterList } from "@app/common/components/Filter/hooks/useFilterList/types";
import { buildFilterGroups } from "@app/common/components/Filter/hooks/useFilterList/utils";
import { EntityFilterCategories, FiltersList } from "@app/common/types/filter";
import { useMemo } from "react";

export const useFilterList = <
  FilterId,
  FilterCategory extends EntityFilterCategories,
>(
  config: FilterConfig<FilterId, FilterCategory>[][],
  filtersList?: FiltersList<FilterCategory>,
): UseFilterList<FilterId, FilterCategory> => {
  return useMemo(
    () => buildFilterGroups(config, filtersList?.filters),
    [config, filtersList],
  );
};
