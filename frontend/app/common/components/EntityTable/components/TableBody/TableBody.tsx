import React from "react";
import { flexRender, RowData, Table } from "@tanstack/react-table";
import { TableBody as MTableBody } from "@mui/material";
import {
  CellComponent as SDSCellComponent,
  TableRow as SDSTableRow,
} from "@czi-sds/components";

interface TableBodyProps<TData extends RowData> {
  table: Table<TData>;
}

export const TableBody = <TData extends RowData>({
  table,
}: TableBodyProps<TData>): JSX.Element => {
  return (
    <MTableBody>
      {table.getRowModel().rows.map((row) => (
        <SDSTableRow key={row.id}>
          {row.getVisibleCells().map((cell) => {
            return (
              <SDSCellComponent key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </SDSCellComponent>
            );
          })}
        </SDSTableRow>
      ))}
    </MTableBody>
  );
};
