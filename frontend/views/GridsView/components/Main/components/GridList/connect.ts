import { useCallback, useContext, useMemo } from "react";
import {
  PaginationState,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { TABLE_OPTIONS } from "@/views/GridsView/components/Main/components/GridList/table/options";
import { GridData } from "@/app/common/types/types";
import { Updater } from "@tanstack/table-core";
import { EntityList } from "@/views/GridsView/components/Main/components/GridList/types";
import { getTableState } from "@/views/GridsView/components/Main/components/GridList/utils";
import { DispatchContext } from "@/views/GridsView/common/store";
import {
  updatePagination,
  updateSort,
} from "@/views/GridsView/common/store/actions/dispatch";

export const useConnect = (gridList?: EntityList<GridData, "grids">) => {
  const dispatch = useContext(DispatchContext);
  const { pagination, sortBy } = gridList || {};
  const state = useMemo(
    () => getTableState({ pagination, sortBy }),
    [pagination, sortBy]
  );

  // Update pagination.
  const onPaginationChange = useCallback(
    (updaterOrValue: Updater<PaginationState>) => {
      dispatch?.(updatePagination({ updaterOrValue, pagination }));
    },
    [dispatch, pagination]
  );

  // Update sorting.
  const onSortingChange = useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      dispatch?.(updateSort({ updaterOrValue, sortBy }));
    },
    [dispatch, sortBy]
  );

  const table = useReactTable<GridData>({
    ...TABLE_OPTIONS,
    data: gridList?.grids || [],
    onPaginationChange,
    onSortingChange,
    rowCount: gridList?.pagination?.totalResults || 0,
    state,
  });

  return { table };
};
