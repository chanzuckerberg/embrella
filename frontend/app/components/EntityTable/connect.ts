import { useCallback, useContext, useMemo } from "react";
import {
  ColumnDef,
  getCoreRowModel,
  PaginationState,
  TableState as ReactTableTableState,
  SortingState,
  TableOptions,
  Updater,
  useReactTable,
} from "@tanstack/react-table";
import {
  getReactTablePaginationState,
  getReactTableSortingState,
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
  UpdatePaginationAction,
  UpdateSortAction,
} from "@/app/common/components/TableStateProvider/TableStateProvider";
import { EntityList, Pagination, SortBy } from "@/app/common/types/tableState";
import { AccessorReturnType } from "../TomogramsView/components/TomogramTable/columns";
import { EntityDataTypes } from "@/app/common/types/tableState";
import { ApiPrimaryEntityAttribute } from "./types";
import { API } from "@/app/common/constants/api";
import { useFetchTableData } from "@/app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@/app/common/types/search";
import {
  getFilterSearchParamValues,
  getPaginationSearchParamValues,
  getSortSearchParamValue,
} from "@/app/common/utils/searchParam";

/*
 * This accesses the object of the attribute that is the main entity of the table,
 * and returns its id as a string.  e.g. row.tomograms.id
 */
const getRowId = (
  row: EntityDataTypes,
  entityApiResponseField: ApiPrimaryEntityAttribute
): string =>
  (row as Record<string, any>)[entityApiResponseField]?.id.toString();

const getDefaultTableOptions = (
  entityApiResponseField: ApiPrimaryEntityAttribute
): Omit<TableOptions<EntityDataTypes>, "data" | "columns"> => ({
  getCoreRowModel: getCoreRowModel(),
  getRowId: (row: EntityDataTypes) => getRowId(row, entityApiResponseField),
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualPagination: true,
  manualSorting: true,
});

export const useConnect = (
  entityApi: API,
  entityApiResponseField: ApiPrimaryEntityAttribute,
  columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[]
) => {
  const state = useContext<TableState>(TableStateContext);
  const dispatch = useContext(TableDispatchContext);

  const entityList = useFetchTableData(entityApi, {
    [SEARCH_PARAM_NAME.QUERY]: [
      ...getFilterSearchParamValues(state),
      ...getPaginationSearchParamValues(state),
      ...getSortSearchParamValue(state),
    ],
  });

  const { pagination: entityPagination, sortBy: entitySortBy } =
    entityList || {};

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
    [dispatch, entitySortBy]
  );

  const table = useReactTable<EntityDataTypes>({
    ...getDefaultTableOptions(entityApiResponseField),
    columns: columnDefs,
    data: entityList?.entities || [],
    onPaginationChange,
    onSortingChange,
    rowCount: entityList?.pagination?.totalResults || 0,
    state: reactTableState,
  });

  return { table };
};
