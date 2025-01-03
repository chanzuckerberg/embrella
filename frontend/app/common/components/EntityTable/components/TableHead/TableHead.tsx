import React, { Fragment } from "react";
import { flexRender, Table } from "@tanstack/react-table";
import { CellHeader, TableHeader } from "@czi-sds/components";
import {
  getCellHeaderActive,
  getCellHeaderDirection,
  getCellHeaderHideSortIcon,
} from "@app/common/components/EntityTable/components/TableHead/utils/cellHeader";
import { EntityDataTypes } from "@app/common/types/tableState";

interface TableHeadProps<TData extends EntityDataTypes> {
  table: Table<TData>;
}

export const TableHead = <TData extends EntityDataTypes>({
  table,
}: TableHeadProps<TData>): JSX.Element => {
  return (
    <TableHeader>
      {table.getFlatHeaders().map((header) => (
        <Fragment key={header.id}>
          <CellHeader
            active={getCellHeaderActive(header)}
            direction={getCellHeaderDirection(header)}
            hideSortIcon={getCellHeaderHideSortIcon(header)}
            key={header.id}
            onClick={header.column.getToggleSortingHandler()}
          >
            {flexRender(header.column.columnDef.header, header.getContext())}
          </CellHeader>
        </Fragment>
      ))}
    </TableHeader>
  );
};
