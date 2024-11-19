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
import { getFilterSearchParamValues } from "@app/common/utils/filter";

const TABLE_OPTIONS: Omit<TableOptions<TomogramData>, "data" | "columns"> = {
  getCoreRowModel: getCoreRowModel(),
  getRowId: (row: TomogramData) => row.tomograms.id.toString(),
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualPagination: true,
  manualSorting: true,
};

const TOMOGRAM_RESPONSE_FIELD = "tomograms" as const;

export const useConnect = () => {
  const state = useContext<TableState>(TableStateContext);

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

  const table = useReactTable<TomogramData>({
    ...TABLE_OPTIONS,
    columns: TOMOGRAM_COLUMN_DEFS,
    data: tomogramList?.tomograms || [],
    rowCount: tomogramList?.tomograms.length || 0,
  });

  return { table };
};
