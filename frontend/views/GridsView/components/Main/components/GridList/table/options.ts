import { TableOptions } from "@tanstack/table-core";
import { getCoreRowModel } from "@tanstack/react-table";
import { GRID_COLUMN_DEFS } from "@/views/GridsView/components/Main/components/GridList/columns/column";
import { getRowId } from "@/views/GridsView/components/Main/components/GridList/utils";
import { GridData } from "@/common/types";

export const TABLE_OPTIONS: Omit<TableOptions<GridData>, "data"> = {
  columns: GRID_COLUMN_DEFS,
  getCoreRowModel: getCoreRowModel(),
  getRowId,
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualSorting: true,
};
