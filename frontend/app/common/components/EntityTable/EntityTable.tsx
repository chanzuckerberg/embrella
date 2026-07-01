import { Fragment, useEffect } from 'react';

import { Pagination } from '@czi-sds/components';
import styled from '@emotion/styled';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  IconButton,
  Collapse,
  Box,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import { ColumnDef, flexRender, Row, RowSelectionState, Updater } from '@tanstack/react-table';

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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getSubRows?: (row: any) => any[] | undefined;
  renderSubRow?: (row: Row<T>) => React.ReactNode;
  onRowCountChange?: (rowCount: number) => void;
}

export const StyledPagination = styled(Pagination)`
  margin-top: 16px;
`;

const ScrollableCell = styled.div<{ maxWidth: number }>`
  max-width: ${(props) => props.maxWidth}px;
  overflow-x: auto;
  white-space: nowrap;
`;

export const StyledTableCell = styled(TableCell, {
  shouldForwardProp: (prop) => prop !== 'width',
})<{ width?: number }>`
  ${(props) => props.width && `width: ${props.width}px;`}
  padding: 12px 16px;
  word-break: break-word;

  a {
    font-size: inherit;
  }
`;

export const StyledHeaderCell = styled(TableCell, {
  shouldForwardProp: (prop) => prop !== 'width',
})<{ width?: number }>`
  ${(props) => props.width && `width: ${props.width}px;`}
  padding: 12px 16px;
  font-weight: 600;
  background-color: #f5f5f5;
`;

function getAriaSort(
  canSort: boolean,
  sorted: false | 'asc' | 'desc'
): 'ascending' | 'descending' | 'none' | undefined {
  if (!canSort) return undefined;
  if (sorted === 'desc') return 'descending';
  if (sorted === 'asc') return 'ascending';
  return 'none';
}

export const EntityTable = <T extends EntityDataTypes>({
  entityApi,
  entityApiResponseField,
  columnDefs,
  rowSelection,
  onRowSelectionChange,
  enableRowSelection = false,
  getSubRows,
  renderSubRow,
  onRowCountChange,
}: EntityTableProps<T>): React.JSX.Element => {
  const { table, entityList } = useConnect<T>(entityApi, entityApiResponseField, columnDefs, {
    rowSelection,
    onRowSelectionChange,
    enableRowSelection,
    getSubRows,
  });

  useEffect(() => {
    if (entityList?.entities) {
      onRowCountChange?.(entityList.entities.length);
    }
  }, [entityList, onRowCountChange]);

  const { getPageCount, getState, nextPage, previousPage, setPageIndex } = table;
  const {
    pagination: { pageIndex, pageSize },
  } = getState();
  // SDS Pagination only accepts totalCount and computes pages as ceil(totalCount/pageSize).
  // We derive a totalCount from the backend's orphan-aware pageCount so the page numbers match.
  const totalCount = getPageCount() * pageSize;

  const columnCount = table.getFlatHeaders().length;

  return (
    <Fragment>
      <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e0e0e0' }}>
        <Table data-testid={TEST_IDS.ENTITY_TABLE} size="small" sx={{ tableLayout: 'fixed', minWidth: 900 }}>
          <TableHead>
            <TableRow>
              {table.getFlatHeaders().map((header) => {
                const width = header.column.columnDef.size;
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();
                const sortDirection = sorted === 'desc' ? 'desc' : 'asc';
                return (
                  <StyledHeaderCell key={header.id} width={width} aria-sort={getAriaSort(canSort, sorted)}>
                    {canSort ? (
                      <TableSortLabel
                        active={!!sorted}
                        direction={sortDirection}
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
            {table.getRowModel().rows.map((row) => {
              // Skip sub-rows in main iteration — they are rendered inline via renderSubRow
              if (row.depth > 0) return null;

              const isExpanded = row.getIsExpanded();
              const canExpand = row.getCanExpand();

              return (
                <Fragment key={row.id}>
                  <TableRow
                    hover
                    sx={canExpand ? { cursor: 'pointer' } : undefined}
                    onClick={canExpand ? () => row.toggleExpanded() : undefined}
                  >
                    {row.getVisibleCells().map((cell, cellIndex) => {
                      const meta = cell.column.columnDef.meta;
                      const width = cell.column.columnDef.size;
                      const content = flexRender(cell.column.columnDef.cell, cell.getContext());
                      return (
                        <StyledTableCell key={cell.id} width={width}>
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              ...(cellIndex === 0 && renderSubRow ? { minHeight: 34 } : {}),
                            }}
                          >
                            {cellIndex === 0 && renderSubRow && !canExpand && (
                              <Box sx={{ width: 30, mr: 0.5, flexShrink: 0 }} />
                            )}
                            {cellIndex === 0 && canExpand && (
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  row.toggleExpanded();
                                }}
                                sx={{ mr: 0.5 }}
                              >
                                {isExpanded ? (
                                  <KeyboardArrowDownIcon fontSize="small" />
                                ) : (
                                  <KeyboardArrowRightIcon fontSize="small" />
                                )}
                              </IconButton>
                            )}
                            {meta?.maxWidth ? (
                              <ScrollableCell maxWidth={meta.maxWidth}>{content}</ScrollableCell>
                            ) : (
                              content
                            )}
                          </Box>
                        </StyledTableCell>
                      );
                    })}
                  </TableRow>

                  {canExpand && renderSubRow && (
                    <TableRow sx={!isExpanded ? { display: 'none' } : undefined}>
                      <TableCell colSpan={columnCount} sx={{ p: 0 }}>
                        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                          <Box sx={{ pl: 4, pr: 2, py: 1, bgcolor: '#fafafa', minWidth: 'fit-content' }}>
                            {renderSubRow(row)}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              );
            })}
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
        totalCount={totalCount}
        truncateDropdown
      />
    </Fragment>
  );
};
