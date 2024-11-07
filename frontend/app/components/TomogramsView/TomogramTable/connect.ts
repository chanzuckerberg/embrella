import { TableOptions } from "@tanstack/table-core";
import { TomogramData } from "@/app/common/types/tomogram";
import { EntityList } from "@/app/common/types/types";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";

const TABLE_OPTIONS: Omit<TableOptions<TomogramData>, "data" | "columns"> = {
  getCoreRowModel: getCoreRowModel(),
  getRowId: (row: TomogramData) => row.tomograms.id.toString(),
  enableMultiSort: false,
  enableSorting: true,
  enableSortingRemoval: false,
  manualPagination: true,
  manualSorting: true,
};

export const useConnect = (
  tomogramList?: EntityList<TomogramData, "tomograms">
) => {
  const table = useReactTable<TomogramData>({
    ...TABLE_OPTIONS,
    columns: TOMOGRAM_COLUMN_DEFS,
    data: tomogramList?.tomograms || [],
    rowCount: tomogramList?.tomograms.length || 0,
  });

  return { table };
};
