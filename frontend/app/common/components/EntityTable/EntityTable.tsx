import { Fragment } from 'react';

import { Pagination } from '@czi-sds/components';
import styled from '@emotion/styled';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel, Paper } from '@mui/material';
import { ColumnDef, flexRender, RowSelectionState, Updater } from '@tanstack/react-table';

import { API } from '@app/common/constants/api';
import { TEST_IDS } from '@app/common/constants/testIds';
import { EntityDataTypes } from '@app/common/types/tableState';

import { useConnect } from './connect';
import { AccessorReturnType, ApiPrimaryEntityAttribute } from './types';

interface EntityTableProps<T> {
  entityApi: API;
  entityApiResponseField: ApiPrimaryEntityAttribute;
  columnDefs: ColumnDef<T, AccessorReturnType>[];
  rowSelection?: RowSelectionState;
  onRowSelectionChange?: (updater: Updater<RowSelectionState>) => void;
  enableRowSelection?: boolean;
}

export const StyledPagination = styled(Pagination)`
  margin-top: 16px;
`;

const ScrollableCell = styled.div<{ maxWidth: number }>`
  max-width: ${(props) => props.maxWidth}px;
  overflow-x: auto;
  white-space: nowrap;
`;

const StyledTableCell = styled(TableCell, {
  shouldForwardProp: (prop) => prop !== 'width',
})<{ width?: number }>`
  ${(props) => props.width && `width: ${props.width}px;`}
  padding: 12px 16px;
`;

const StyledHeaderCell = styled(TableCell, {
  shouldForwardProp: (prop) => prop !== 'width',
})<{ width?: number }>`
  ${(props) => props.width && `width: ${props.width}px;`}
  padding: 12px 16px;
  font-weight: 600;
  background-color: #f5f5f5;
`;

export const EntityTable = <T extends EntityDataTypes>({
  entityApi,
  entityApiResponseField,
  columnDefs,
  rowSelection,
  onRowSelectionChange,
  enableRowSelection = false,
}: EntityTableProps<T>): React.JSX.Element => {
  const { table } = useConnect<T>(entityApi, entityApiResponseField, columnDefs, {
    rowSelection,
    onRowSelectionChange,
    enableRowSelection,
  });

  const { getRowCount, getState, nextPage, previousPage, setPageIndex } = table;
  const {
    pagination: { pageIndex, pageSize },
  } = getState();

  return (
    <Fragment>
      <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e0e0e0' }}>
        <Table data-testid={TEST_IDS.ENTITY_TABLE} size="small">
          <TableHead>
            <TableRow>
              {table.getFlatHeaders().map((header) => {
                const width = header.column.columnDef.size;
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();
                return (
                  <StyledHeaderCell key={header.id} width={width}>
                    {canSort ? (
                      <TableSortLabel
                        active={!!sorted}
                        direction={sorted === 'desc' ? 'desc' : 'asc'}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </TableSortLabel>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </StyledHeaderCell>
                );
              })}
            </TableRow>
          </TableHead>

          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} hover>
                {row.getVisibleCells().map((cell) => {
                  const meta = cell.column.columnDef.meta as { maxWidth?: number } | undefined;
                  const width = cell.column.columnDef.size;
                  const content = flexRender(cell.column.columnDef.cell, cell.getContext());
                  return (
                    <StyledTableCell key={cell.id} width={width}>
                      {meta?.maxWidth ? <ScrollableCell maxWidth={meta.maxWidth}>{content}</ScrollableCell> : content}
                    </StyledTableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

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
