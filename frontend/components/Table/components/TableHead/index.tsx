import React, { Fragment } from "react";
import { flexRender, RowData } from "@tanstack/react-table";
import { Props } from "@/components/Table/components/TableHead/types";
import {
  CellHeader as SDSCellHeader,
  TableHeader as SDSTableHeader,
} from "@czi-sds/components";
import {
  getCellHeaderActive,
  getCellHeaderDirection,
  getCellHeaderHideSortIcon,
} from "@/components/Table/components/TableHead/utils";

export const TableHead = <TData extends RowData>({
  table,
}: Props<TData>): JSX.Element => {
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
