import React from "react";
import { flexRender, RowData } from "@tanstack/react-table";
import { Props } from "@/app/common/components/Table/components/TableBody/types";
import { TableBody as MTableBody } from "@mui/material";
import {
  CellComponent as SDSCellComponent,
  TableRow as SDSTableRow,
} from "@czi-sds/components";

export const TableBody = <TData extends RowData>({
  table,
}: Props<TData>): JSX.Element => {
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
