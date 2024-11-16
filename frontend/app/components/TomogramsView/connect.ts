import { useCallback, useContext } from "react";

import { API } from "@app/common/constants/api";
import { useFetchFilters } from "@app/common/hooks/useFetchFilters/useFetchFilters";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import { TomogramData } from "@app/common/types/tomogram";
import { getFilterSearchParamValues } from "@app/common/utils/filter";
import {
  DispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
  UpdateFilterAction,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { useFilterList } from "../Filter/hooks/useFilterList/useFilterList";
import {
  TOMOGRAM_FILTER_ID,
  TomogramFilterCategory,
} from "@app/common/types/filter";
import { TOMOGRAM_FILTER_CONFIGS } from "@app/components/TomogramsView/TomogramTable/filters";
import { CategoryFilter } from "@app/components/Filter/common/types";
import { UpdateFilterPayload } from "@/views/GridsView/common/store/actions/types";

const TOMOGRAM_RESPONSE_FIELD = "tomograms" as const;

export const useConnect = () => {
  const state = useContext<TableState>(TableStateContext);
  const dispatch = useContext(DispatchContext);

  const tomogramList = useFetchTableData<
    TomogramData,
    typeof TOMOGRAM_RESPONSE_FIELD
  >(
    API.TOMOGRAMS_V1,
    {
      [SEARCH_PARAM_NAME.QUERY]: [
        ...getFilterSearchParamValues(state),
        // TODO: re-enable when pagination and sort are implemented.
        // ...getPaginationSearchParamValue(state),
        // ...getSortSearchParamValue(state)
      ],
    },
    TOMOGRAM_RESPONSE_FIELD
  );

  const filtersList = useFetchFilters(API.TOMOGRAMS_FILTERLIST_V1, {
    [SEARCH_PARAM_NAME.QUERY]: getFilterSearchParamValues(state),
  });

  const filters = useFilterList<TOMOGRAM_FILTER_ID, TomogramFilterCategory>(
    TOMOGRAM_FILTER_CONFIGS,
    filtersList
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
    [dispatch, filtersList]
  );

  return { tomogramList, filters, onFilter };
};
