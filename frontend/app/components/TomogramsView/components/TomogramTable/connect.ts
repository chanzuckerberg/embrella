import { TableOptions } from "@tanstack/table-core";
import { TomogramData } from "@app/common/types/tomogram";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";
import { useContext } from "react";
import {
  TableState,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { API } from "@app/common/constants/api";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import { getFilterSearchParamValues } from "@app/common/utils/searchParam";

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

  const tomogramList = useFetchTableData<typeof TOMOGRAM_RESPONSE_FIELD>(
    API.TOMOGRAMS_V1,
    {
      [SEARCH_PARAM_NAME.QUERY]: [
        ...getFilterSearchParamValues(state),
        // TODO: re-enable when pagination and sort are implemented.
        // these functions should be implemented in frontend/app/common/utils/filter.ts (plan to rename to searchParam.ts)
        // ...getPaginationSearchParamValue(state),
        // ...getSortSearchParamValue(state)
      ],
    },
    TOMOGRAM_RESPONSE_FIELD
  );

  // TODO: add onPaginationChange, onSortingChange callback functions and pass to useReactTable
  // const onPaginationChange = useCallback(
  //   (updaterOrValue: Updater<PaginationState>) => {
  //     dispatch?.(updatePagination({ updaterOrValue, pagination }));
  //   },
  //   [dispatch, pagination]
  // );

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
    rowCount: tomogramList?.tomograms.length || 0,
  });

  return { table };
};
