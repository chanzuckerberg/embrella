import React, { Fragment } from "react";
import { flexRender, RowData, Table } from "@tanstack/react-table";
import {
  CellHeader as SDSCellHeader,
  TableHeader as SDSTableHeader,
} from "@czi-sds/components";
import {
  getCellHeaderActive,
  getCellHeaderDirection,
  getCellHeaderHideSortIcon,
} from "@app/common/components/EntityTable/components/TableHead/utils/cellHeader";

interface TableHeadProps<TData extends RowData> {
  table: Table<TData>;
}

export const TableHead = <TData extends RowData>({
  table,
}: TableHeadProps<TData>): JSX.Element => {
  return (
    <SDSTableHeader>
      {table.getFlatHeaders().map((header) => (
        <Fragment key={header.id}>
          <SDSCellHeader
            active={getCellHeaderActive(header)}
            direction={getCellHeaderDirection(header)}
            hideSortIcon={getCellHeaderHideSortIcon(header)}
            key={header.id}
            onClick={header.column.getToggleSortingHandler()}
          >
            {flexRender(header.column.columnDef.header, header.getContext())}
          </SDSCellHeader>
        </Fragment>
      ))}
    </SDSTableHeader>
  );
};
