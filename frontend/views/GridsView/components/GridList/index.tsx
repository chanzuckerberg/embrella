import React, { useMemo } from "react";
import { Props } from "@/views/GridsView/components/GridList/types";
import { GRID_COLUMN_DEFS } from "@/views/GridsView/components/GridList/columns/column";
import {
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { GridData } from "@/common/types";
import { TableHead } from "@/components/Table/components/TableHead";
import { TableBody } from "@/components/Table/components/TableBody";
import { getRowId } from "@/views/GridsView/components/GridList/utils";
import { Table as SDSTable } from "@czi-sds/components";
import { TEST_ID_GRIDS } from "./common/constants";

export const GridList = ({ gridList = [] }: Props): JSX.Element => {
  const columns = useMemo(() => GRID_COLUMN_DEFS, []);
  const table = useReactTable<GridData>({
    columns,
    data: gridList,
    enableSorting: false,
    getCoreRowModel: getCoreRowModel(),
    getRowId,
    getSortedRowModel: getSortedRowModel(),
  });
  return (
    <SDSTable data-testid={TEST_ID_GRIDS}>
      <TableHead table={table} />
      <TableBody table={table} />
    </SDSTable>
  );
};
