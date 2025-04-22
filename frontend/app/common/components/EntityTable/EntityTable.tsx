import { Fragment } from "react";

import {
  CellComponent,
  CellHeader,
  Pagination,
  Table,
  TableHeader,
  TableRow,
} from "@czi-sds/components";
import styled from "@emotion/styled";
import { TableBody } from "@mui/material";
import { ColumnDef, flexRender } from "@tanstack/react-table";

import { GET_API } from "@app/common/constants/api";
import { TEST_IDS } from "@app/common/constants/testIds";
import { EntityDataTypes } from "@app/common/types/tableState";

import { useConnect } from "./connect";
import { AccessorReturnType, ApiPrimaryEntityAttribute } from "./types";
import {
  getCellHeaderActive,
  getCellHeaderDirection,
  getCellHeaderHideSortIcon,
} from "./utils/cellHeader";

interface EntityTableProps {
  entityApi: GET_API;
  entityApiResponseField: ApiPrimaryEntityAttribute;
  columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[];
}

export const StyledPagination = styled(Pagination)`
  margin-top: 16px;
`;

export const EntityTable = ({
  entityApi,
  entityApiResponseField,
  columnDefs,
}: EntityTableProps): React.JSX.Element => {
  const { table } = useConnect(entityApi, entityApiResponseField, columnDefs);

  const { getRowCount, getState, nextPage, previousPage, setPageIndex } = table;
  const {
    pagination: { pageIndex, pageSize },
  } = getState();

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

      <StyledPagination
        currentPage={pageIndex + 1}
        data-testid={TEST_IDS.ENTITY_TABLE_PAGINATION}
        onNextPage={nextPage}
        onPageChange={(page) => setPageIndex(page - 1)}
        onPreviousPage={previousPage}
        pageSize={pageSize}
        totalCount={getRowCount()}
        truncateDropdown
      />
    </Fragment>
  );
};
