import {
  PaginationState,
  TableOptions,
  Updater,
  TableState as ReactTableTableState,
  SortingState,
} from "@tanstack/table-core";
import { TomogramData } from "@app/common/types/tomogram";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";
import { useCallback, useContext, useMemo } from "react";
import {
  getReactTablePaginationState,
  getReactTableSortingState,
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
  UpdatePaginationAction,
  UpdateSortAction,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { API } from "@app/common/constants/api";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import {
  getFilterSearchParamValues,
  getPaginationSearchParamValues,
  getSortSearchParamValue,
} from "@app/common/utils/searchParam";
import { Pagination, SortBy } from "@app/common/types/types";

const TABLE_OPTIONS: Omit<TableOptions<TomogramData>, "data" | "columns"> = {
  getCoreRowModel: getCoreRowModel(),
  getRowId: (row: TomogramData) => row.tomograms.id.toString(),
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualPagination: true,
  manualSorting: true,
};

const TOMOGRAM_RESPONSE_FIELD = "tomograms";

export const useConnect = () => {
  const state = useContext<TableState>(TableStateContext);
  const dispatch = useContext(TableDispatchContext);

  const tomogramList = useFetchTableData<typeof TOMOGRAM_RESPONSE_FIELD>(
    API.TOMOGRAMS_V1,
    {
      [SEARCH_PARAM_NAME.QUERY]: [
        ...getFilterSearchParamValues(state),
        ...getPaginationSearchParamValues(state),
        ...getSortSearchParamValue(state),
      ],
    },
    TOMOGRAM_RESPONSE_FIELD
  );

  const { pagination: entityPagination, sortBy: entitySortBy } =
    tomogramList || {};

  const reactTableState: Partial<ReactTableTableState> = useMemo(
    () => ({
      pagination: getReactTablePaginationState(entityPagination as Pagination),
      sorting: getReactTableSortingState(entitySortBy as SortBy),
    }),
    [entityPagination, entitySortBy]
  );

  const onPaginationChange = useCallback(
    (updaterOrValue: Updater<PaginationState>): void => {
      const updatePaginationAction: UpdatePaginationAction = {
        payload: {
          pagination: entityPagination,
          updaterOrValue,
        },
        type: TableStateActionTypes.UpdatePagination,
      };

      dispatch(updatePaginationAction);
    },
    [dispatch, entityPagination]
  );

  const onSortingChange = useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      const updateSortAction: UpdateSortAction = {
        payload: {
          sortBy: entitySortBy,
          updaterOrValue,
        },
        type: TableStateActionTypes.UpdateSort,
      };

      dispatch(updateSortAction);
    },
    [dispatch, tomogramList?.sortBy]
  );

  const table = useReactTable<TomogramData>({
    ...TABLE_OPTIONS,
    columns: TOMOGRAM_COLUMN_DEFS,
    data: tomogramList?.tomograms || [],
    onPaginationChange,
    onSortingChange,
    rowCount: tomogramList?.pagination?.totalResults || 0,
    state: reactTableState,
  });

  return { table };
};
