import { useCallback, useContext } from "react";
import { Props } from "./types";
import { DispatchContext } from "@/views/GridsView/common/store";
import { CategoryFilter } from "@/app/components/Filter/common/types";
import { GridFilterCategory } from "@/common/types";
import { useFilterList } from "@/app/components/Filter/hooks/useFilterList/useFilterList";
import { GRID_FILTER_ID } from "@/views/GridsView/components/Main/components/GridFilter/filters/types";
import { GRID_FILTER_CONFIGS } from "@/views/GridsView/components/Main/components/GridFilter/filters/filter";
import { updateFilter } from "@/views/GridsView/common/store/actions/dispatch";

export const useConnect = ({
  filtersList,
}: {
  filtersList: Props["filtersList"];
}) => {
  const dispatch = useContext(DispatchContext);

  // Build filter groups with the filter list and the filter config.
  const filters = useFilterList<GRID_FILTER_ID, GridFilterCategory>(
    GRID_FILTER_CONFIGS,
    filtersList
  );

  // Update filter.
  const onFilter = useCallback(
    (categoryFilter: CategoryFilter<GridFilterCategory>): void => {
      dispatch?.(updateFilter({ categoryFilter, filtersList }));
    },
    [dispatch, filtersList]
  );

  return {
    filters,
    onFilter,
  };
};
