import { useCallback, useContext, useMemo } from "react";
import { SortingState, useReactTable } from "@tanstack/react-table";
import { TABLE_OPTIONS } from "@/views/GridsView/components/Main/components/GridList/table/options";
import { EntityList, GridData } from "@/common/types";
import { Updater } from "@tanstack/table-core";
import { getTableState } from "@/views/GridsView/components/Main/components/GridList/utils";
import { DispatchContext } from "@/views/GridsView/common/store";
import { updateSort } from "@/views/GridsView/common/store/actions/dispatch";

export const useConnect = (gridList?: EntityList<GridData, "grids">) => {
  const dispatch = useContext(DispatchContext);
  const { sortBy } = gridList || {};
  const state = useMemo(() => getTableState({ sortBy }), [sortBy]);

  // Update sorting.
  const onSortingChange = useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      dispatch?.(updateSort({ updaterOrValue, sortBy }));
    },
    [dispatch, sortBy],
  );

  const table = useReactTable<GridData>({
    ...TABLE_OPTIONS,
    data: gridList?.grids || [],
    onSortingChange,
    state,
  });

  return { table };
};
