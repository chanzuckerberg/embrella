import { Fragment } from "react";

import {
  CellComponent,
  CellHeader,
  Table,
  TableHeader,
  TableRow,
} from "@czi-sds/components";
import { TableBody } from "@mui/material";
import { ColumnDef, flexRender } from "@tanstack/react-table";

import { API } from "@app/common/constants/api";
import { TEST_IDS } from "@app/common/constants/testIds";
import { EntityDataTypes } from "@app/common/types/tableState";

import { Pagination } from "./components/Pagination/Pagination";
import { useConnect } from "./connect";
import { AccessorReturnType, ApiPrimaryEntityAttribute } from "./types";
import {
  getCellHeaderActive,
  getCellHeaderDirection,
  getCellHeaderHideSortIcon,
} from "./utils/cellHeader";

interface EntityTableProps {
  entityApi: API;
  entityApiResponseField: ApiPrimaryEntityAttribute;
  columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[];
}

export const EntityTable = ({
  entityApi,
  entityApiResponseField,
  columnDefs,
}: EntityTableProps): React.JSX.Element => {
  const { table } = useConnect(entityApi, entityApiResponseField, columnDefs);

  return (
    <Fragment>
      <Table data-testid={TEST_IDS.ENTITY_TABLE}>
        <TableHeader>
          {table.getFlatHeaders().map((header) => (
            <CellHeader
              active={getCellHeaderActive(header)}
              direction={getCellHeaderDirection(header)}
              hideSortIcon={getCellHeaderHideSortIcon(header)}
              key={header.id}
              onClick={header.column.getToggleSortingHandler()}
            >
              {flexRender(header.column.columnDef.header, header.getContext())}
            </CellHeader>
          ))}
        </TableHeader>

        <TableBody>
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
        </TableBody>
      </Table>
      <Pagination dataTestId={TEST_IDS.ENTITY_TABLE_PAGINATION} table={table} />
    </Fragment>
  );
};
