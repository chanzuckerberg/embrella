import { useCallback, useContext } from "react";

import {
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { UpdateFilterAction } from "@app/common/components/TableStateProvider/TableStateProvider";
import {
  CategoryFilter,
  FilterConfig,
} from "@app/common/components/Filter/common/types";
import { UseFilterList } from "@app/common/components/Filter/hooks/useFilterList/types";
import { useFilterList } from "@app/common/components/Filter/hooks/useFilterList/useFilterList";
import { useFetchFilters } from "@app/common/hooks/useFetchFilters/useFetchFilters";
import { API } from "@app/common/constants/api";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import { getFilterSearchParamValues } from "@app/common/utils/searchParam";
import {
  EntityFilterCategories,
  EntityFilterConfigs,
  EntityFilterIdTypes,
} from "@app/common/types/filter";

export interface EntityTableFilterConnect<
  FilterId extends EntityFilterIdTypes,
  FilterCategory extends EntityFilterCategories,
> {
  filters: UseFilterList<FilterId, FilterCategory>;
  onFilter: (categoryFilter: CategoryFilter<FilterCategory>) => void;
}

export const useConnect = <
  FilterId extends EntityFilterIdTypes,
  FilterCategory extends EntityFilterCategories,
>(
  entityFilterConfigs: EntityFilterConfigs[][],
  entityFilterListApi: API,
): EntityTableFilterConnect<FilterId, FilterCategory> => {
  console.log("entityFilterConfigs", entityFilterConfigs);
  const dispatch = useContext(TableDispatchContext);

  const state = useContext<TableState>(TableStateContext);

  const filtersList = useFetchFilters(entityFilterListApi, {
    [SEARCH_PARAM_NAME.QUERY]: getFilterSearchParamValues(state),
  });

  const filters = useFilterList<FilterId, FilterCategory>(
    entityFilterConfigs as FilterConfig<FilterId, FilterCategory>[][],
    filtersList,
  );

  const onFilter = useCallback(
    (categoryFilter: CategoryFilter<FilterCategory>): void => {
      const updateFilterAction: UpdateFilterAction = {
        payload: {
          categoryFilter,
        },
        type: TableStateActionTypes.UpdateFilter,
      };
      dispatch(updateFilterAction);
    },
    [dispatch],
  );

  return { filters, onFilter };
};
