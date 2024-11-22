import { useCallback, useContext } from "react";

import {
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { UpdateFilterAction } from "@app/common/components/TableStateProvider/TableStateProvider";
import {
  TOMOGRAM_FILTER_CONFIGS,
  TOMOGRAM_FILTER_ID,
  TomogramFilterCategory,
} from "@app/components/TomogramsView/types";
import { CategoryFilter } from "@app/components/Filter/common/types";
import { useFilterList } from "@app/components/Filter/hooks/useFilterList/useFilterList";
import { useFetchFilters } from "@app/common/hooks/useFetchFilters/useFetchFilters";
import { API } from "@app/common/constants/api";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import { getFilterSearchParamValues } from "@app/common/utils/searchParam";

export const useConnect = () => {
  const dispatch = useContext(TableDispatchContext);

  const state = useContext<TableState>(TableStateContext);

  const filtersList = useFetchFilters(API.TOMOGRAMS_FILTERLIST_V1, {
    [SEARCH_PARAM_NAME.QUERY]: getFilterSearchParamValues(state),
  });

  const filters = useFilterList<TOMOGRAM_FILTER_ID, TomogramFilterCategory>(
    TOMOGRAM_FILTER_CONFIGS,
    filtersList,
  );

  const onFilter = useCallback(
    (categoryFilter: CategoryFilter<TomogramFilterCategory>): void => {
      const updateFilterAction: UpdateFilterAction = {
        payload: {
          categoryFilter,
          filtersList,
        },
        type: TableStateActionTypes.UpdateFilter,
      };
      dispatch(updateFilterAction);
    },
    [dispatch, filtersList],
  );

  return { filters, onFilter };
};
