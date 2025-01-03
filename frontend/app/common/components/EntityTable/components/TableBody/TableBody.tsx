import React from "react";
import { flexRender, Table } from "@tanstack/react-table";
import { TableBody as MTableBody } from "@mui/material";
import { CellComponent, TableRow } from "@czi-sds/components";
import { EntityDataTypes } from "@app/common/types/tableState";

interface TableBodyProps<TData extends EntityDataTypes> {
  table: Table<TData>;
}

export const TableBody = <TData extends EntityDataTypes>({
  table,
}: TableBodyProps<TData>): JSX.Element => {
  return (
    <MTableBody>
      {table.getRowModel().rows.map((row) => (
        <TableRow key={row.id}>
          {row.getVisibleCells().map((cell) => {
            return (
              <CellComponent key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </CellComponent>
            );
          })}
        </TableRow>
      ))}
    </MTableBody>
  );
};
