import {
  PaginationState,
  TableOptions,
  Updater,
  TableState as ReactTableTableState,
} from "@tanstack/table-core";
import { TomogramData } from "@app/common/types/tomogram";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";
import { useCallback, useContext, useMemo, useState } from "react";
import {
  getReactTablePaginationState,
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
  UpdatePaginationAction,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { API } from "@app/common/constants/api";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import {
  getFilterSearchParamValues,
  getPaginationSearchParamValues,
} from "@app/common/utils/searchParam";
import { Pagination } from "@app/common/types/types";

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
        // TODO: re-enable when pagination and sort are implemented.
        // ...getSortSearchParamValue(state)
      ],
    },
    TOMOGRAM_RESPONSE_FIELD
  );

  const { pagination: entityPagination, sortBy: entitySortBy } =
    tomogramList || {};

  const pagination: PaginationState = getReactTablePaginationState(
    entityPagination as Pagination
  );

  const reactTableState: Partial<ReactTableTableState> = useMemo(
    () => ({
      pagination,
      // sorting: getSortingState(sortBy),
    }),
    [entityPagination /*sortBy*/]
  );

  const onPaginationChange = useCallback(
    (updaterOrValue: Updater<PaginationState>): void => {
      state.paginationState;
      const updatePaginationAction: UpdatePaginationAction = {
        payload: {
          pagination: tomogramList?.pagination,
          updaterOrValue,
        },
        type: TableStateActionTypes.UpdatePagination,
      };
      dispatch(updatePaginationAction);
    },
    [dispatch, tomogramList?.pagination]
  );

  // const onSortingChange = useCallback(
  //   (updaterOrValue: Updater<SortingState>) => {
  //     dispatch?.(updateSort({ updaterOrValue, sortBy }));
  //   },
  //   [dispatch, sortBy]
  // );

  const table = useReactTable<TomogramData>({
    ...TABLE_OPTIONS,
    columns: TOMOGRAM_COLUMN_DEFS,
    data: tomogramList?.tomograms || [],
    onPaginationChange,
    // onSortingChange,
    rowCount: tomogramList?.pagination?.totalResults || 0,
    state: reactTableState,
  });

  return { table };
};
