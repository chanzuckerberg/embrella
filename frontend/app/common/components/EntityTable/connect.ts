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
  DEFAULT_PAGE_SIZE,
  TableDispatchContext,
  TableState,
  TableStateActionTypes,
  TableStateContext,
  UpdatePaginationAction,
  UpdateSortAction,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { Pagination, SortBy } from "@app/common/types/tableState";
import { EntityDataTypes } from "@app/common/types/tableState";
import { ApiPrimaryEntityAttribute } from "./types";
import { API } from "@app/common/constants/api";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import {
  getFilterSearchParamValues,
  getPaginationSearchParamValues,
  getSortSearchParamValue,
} from "@app/common/utils/searchParam";
import {
  EntityAPIPrimaryAttributeToDataType,
  EntityLinkField,
} from "@app/common/types/entity";

export const getRowId = <K extends keyof EntityAPIPrimaryAttributeToDataType>(
  row: EntityDataTypes,
  entityApiResponseField: K,
): string => {
  // This function needs to access the attribute of an entity object in the API response to use as the row ID.
  // Due to the primary attribute differing depending on the endpoint, typecasting is needed to satisfy TypeScript.
  // Example of data access: row.tomograms.id
  const typedRow = row as EntityAPIPrimaryAttributeToDataType[K];
  const typedEntityAttribute =
    entityApiResponseField as unknown as keyof EntityAPIPrimaryAttributeToDataType[K];
  const entity = typedRow[typedEntityAttribute] as EntityLinkField;

  return entity.id.toString();
};

const getDefaultTableOptions = <T extends EntityDataTypes>(
  entityApiResponseField: ApiPrimaryEntityAttribute,
): Omit<TableOptions<T>, "data" | "columns"> => ({
  getCoreRowModel: getCoreRowModel(),
  getRowId: (row: T) => getRowId(row, entityApiResponseField),
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualPagination: true,
  manualSorting: true,
});

const getPaginationStateForPayload = (
  pagination: Pagination,
): PaginationState =>
  !pagination
    ? { pageIndex: 0, pageSize: DEFAULT_PAGE_SIZE }
    : {
        pageIndex: pagination.page - 1,
        pageSize: pagination.pageSize,
      };

const getSortingStateForPayload = (sortBy: SortBy): SortingState =>
  !sortBy ? [] : [{ id: sortBy.sort, desc: !sortBy.asc }];

export const useConnect = <T extends EntityDataTypes>(
  entityApi: API,
  entityApiResponseField: ApiPrimaryEntityAttribute,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columnDefs: ColumnDef<T, any>[],
) => {
  const state = useContext<TableState>(TableStateContext);
  const dispatch = useContext(TableDispatchContext);

  const entityList = useFetchTableData<T>(entityApi, {
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
      pagination: getPaginationStateForPayload(entityPagination),
      sorting: getSortingStateForPayload(entitySortBy),
    }),
    [entityPagination, entitySortBy],
  );

  const onPaginationChange = useCallback(
    (updaterOrValue: Updater<PaginationState>): void => {
      const pagination = getPaginationStateForPayload(entityPagination);
      const updatePaginationAction: UpdatePaginationAction = {
        payload: {
          pagination,
          updaterOrValue,
        },
        type: TableStateActionTypes.UpdatePagination,
      };

      dispatch(updatePaginationAction);
    },
    [dispatch, entityPagination],
  );

  const onSortingChange = useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      const sortBy = getSortingStateForPayload(entitySortBy);
      const updateSortAction: UpdateSortAction = {
        payload: {
          sortBy,
          updaterOrValue,
        },
        type: TableStateActionTypes.UpdateSort,
      };

      dispatch(updateSortAction);
    },
    [dispatch, entitySortBy],
  );

  const table = useReactTable<T>({
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
