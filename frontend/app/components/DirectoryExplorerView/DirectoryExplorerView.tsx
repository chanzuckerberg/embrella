'use client';

import React, { useState, useMemo, useCallback, useEffect, Fragment, useContext } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Collapse,
  CircularProgress,
  Typography,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { Pagination } from '@czi-sds/components';
import styled from '@emotion/styled';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  RowSelectionState,
  SortingState,
  useReactTable,
} from '@tanstack/react-table';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { EntityDataTypes } from '@app/common/types/tableState';
import { TableStateProvider, TableStateContext } from '@app/common/components/TableStateProvider/TableStateProvider';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { API } from '@app/common/constants/api';

import { DirectoryFilterCategory, DirectorySummary, isActionablePath } from './types';
import { fetchDirectories } from './api';
import { DIRECTORY_COLUMN_DEFS, DIRECTORY_COLUMN_IDS, createActionColumn } from './constants/columns';
import { DIRECTORY_FILTER_CONFIGS } from './constants/filters';
import { SurveySelector, DirectoryStatsCard, DirectoryBulkActionsBar, DirectoryFilesDrawer } from './components';

const StyledPagination = styled(Pagination)`
  margin-top: 16px;
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

const DEFAULT_PAGE_SIZE = 25;

/**
 * Inner component that uses the TableStateContext for filter state.
 */
const DirectoryExplorerContent = (): React.JSX.Element => {
  // Get filter state from context
  const { filterState } = useContext(TableStateContext);

  // Survey selection
  const [selectedSurveyId, setSelectedSurveyId] = useState<number | null>(null);

  // Table data state
  const [directories, setDirectories] = useState<DirectorySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Sorting state
  const [sorting, setSorting] = useState<SortingState>([{ id: DIRECTORY_COLUMN_IDS.PATH, desc: false }]);

  // Row selection state
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  // Refresh key to trigger data refetch after actions
  const [refreshKey, setRefreshKey] = useState(0);

  // Path search state with debounce
  const [pathSearch, setPathSearch] = useState<string>('');
  const [debouncedPathSearch, setDebouncedPathSearch] = useState<string>('');

  // Debounce path search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedPathSearch(pathSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [pathSearch]);

  // Reset path search when survey changes
  useEffect(() => {
    setPathSearch('');
    setDebouncedPathSearch('');
  }, [selectedSurveyId]);

  // Get selected directory IDs
  const selectedIds = useMemo(() => {
    return Object.keys(rowSelection)
      .filter((id) => rowSelection[id])
      .map((id) => parseInt(id, 10));
  }, [rowSelection]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setRowSelection({});
  }, []);

  // Handle action completion (triggers data refresh)
  const handleActionComplete = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  // Handle survey change
  const handleSurveyChange = useCallback((surveyId: number | null) => {
    setSelectedSurveyId(surveyId);
    setPage(1);
    setRowSelection({});
  }, []);

  // Extract filter values from filterState
  const getFilterValue = useCallback(
    (category: DirectoryFilterCategory): string | undefined => {
      const value = filterState[category];
      if (Array.isArray(value)) {
        return value.length > 0 ? String(value[0]) : undefined;
      }
      return value !== null && value !== undefined ? String(value) : undefined;
    },
    [filterState]
  );

  // Fetch directories when survey, page, sorting, or filters change
  useEffect(() => {
    if (!selectedSurveyId) {
      setDirectories([]);
      return;
    }

    const loadDirectories = async () => {
      setLoading(true);
      setError(null);
      try {
        const sortField = sorting.length > 0 ? sorting[0].id : 'path';
        const sortOrder = sorting.length > 0 && sorting[0].desc ? 'desc' : 'asc';

        const response = await fetchDirectories(selectedSurveyId, {
          page,
          pageSize,
          sortField,
          sortOrder,
          cluster: getFilterValue('cluster'),
          origin: getFilterValue('origin'),
          preserveStatus: getFilterValue('preserve_status'),
          ownerUsername: getFilterValue('owner_username'),
          pathContains: debouncedPathSearch || undefined,
        });

        setDirectories(response.directories);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load directories');
      } finally {
        setLoading(false);
      }
    };

    loadDirectories();
  }, [selectedSurveyId, page, pageSize, sorting, refreshKey, filterState, getFilterValue, debouncedPathSearch]);

  // Reset to page 1 when filters or search change
  useEffect(() => {
    setPage(1);
  }, [filterState, debouncedPathSearch]);

  // Column definitions with action column
  const columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[] = useMemo(
    () => [...DIRECTORY_COLUMN_DEFS, createActionColumn(handleActionComplete)],
    [handleActionComplete]
  );

  // Table instance
  const table = useReactTable<DirectorySummary>({
    data: directories,
    columns: columnDefs as ColumnDef<DirectorySummary, AccessorReturnType>[],
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowId: (row) => row.id.toString(),
    manualPagination: true,
    manualSorting: true,
    enableMultiSort: false,
    enableSorting: true,
    enableSortingRemoval: false,
    enableRowSelection: (row) => isActionablePath(row.original.path),
    state: {
      sorting,
      rowSelection,
    },
    onSortingChange: (updater) => {
      setSorting(typeof updater === 'function' ? updater(sorting) : updater);
      setPage(1); // Reset to first page on sort change
    },
    onRowSelectionChange: (updater) => {
      setRowSelection(typeof updater === 'function' ? updater(rowSelection) : updater);
    },
    rowCount: totalCount,
  });

  // Build filterlist API URL with survey_id
  const filterListApi = selectedSurveyId
    ? (`${API.DIRECTORIES_FILTERLIST}?survey_id=${selectedSurveyId}` as API)
    : ('' as API);

  return (
    <FilterableTableMain>
      <Sidebar>
        {selectedSurveyId ? (
          <>
            <EntityTableFilters entityFilterConfigs={DIRECTORY_FILTER_CONFIGS} entityFilterListApi={filterListApi} />
            <Box sx={{ mt: 2 }}>
              <TextField
                size="small"
                placeholder="Search path..."
                value={pathSearch}
                onChange={(e) => setPathSearch(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                }}
                fullWidth
              />
            </Box>
          </>
        ) : (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Select a survey to see filter options.
            </Typography>
          </Box>
        )}
      </Sidebar>
      <Box sx={{ padding: '8px 24px', '@media (max-width: 900px)': { padding: '8px' } }}>
        {/* Header with Survey Selector */}
        <Box sx={{ mb: 3 }}>
          <SurveySelector selectedSurveyId={selectedSurveyId} onSurveyChange={handleSurveyChange} />
        </Box>

        {/* Stats Card */}
        <DirectoryStatsCard surveyId={selectedSurveyId} />

        {/* Loading State */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Error State */}
        {!!error && (
          <Box sx={{ p: 2 }}>
            <Typography color="error">{error}</Typography>
          </Box>
        )}

        {/* No Survey Selected */}
        {!selectedSurveyId && !loading && (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">Select a survey above to view directory data.</Typography>
          </Box>
        )}

        {/* Table */}
        {!!selectedSurveyId && !loading && !error && (
          <Fragment>
            <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e0e0e0' }}>
              <Table size="small">
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
                  {table.getRowModel().rows.map((row) => {
                    const isExpanded = row.getIsExpanded();
                    const directory = row.original;
                    return (
                      <Fragment key={row.id}>
                        <TableRow hover selected={row.getIsSelected()}>
                          {row.getVisibleCells().map((cell) => {
                            const width = cell.column.columnDef.size;
                            return (
                              <StyledTableCell key={cell.id} width={width}>
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                              </StyledTableCell>
                            );
                          })}
                        </TableRow>
                        {/* Expandable row for files */}
                        <TableRow>
                          <TableCell
                            colSpan={columnDefs.length}
                            sx={{ p: 0, borderBottom: isExpanded ? '1px solid #e0e0e0' : 'none' }}
                          >
                            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                              <DirectoryFilesDrawer directoryId={directory.id} directoryPath={directory.path} />
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Pagination */}
            <StyledPagination
              currentPage={page}
              onNextPage={() => setPage((p) => Math.min(p + 1, totalPages))}
              onPageChange={(newPage) => setPage(newPage)}
              onPreviousPage={() => setPage((p) => Math.max(p - 1, 1))}
              pageSize={pageSize}
              totalCount={totalCount}
              truncateDropdown
            />
          </Fragment>
        )}

        {/* Bulk Actions Bar */}
        <DirectoryBulkActionsBar
          selectedIds={selectedIds}
          onActionComplete={handleActionComplete}
          onClearSelection={clearSelection}
        />
      </Box>
    </FilterableTableMain>
  );
};

/**
 * Main component wrapped with TableStateProvider for filter state management.
 */
export const DirectoryExplorerView = (): React.JSX.Element => {
  return (
    <TableStateProvider initialSortState={[{ id: DIRECTORY_COLUMN_IDS.PATH, desc: false }]}>
      <DirectoryExplorerContent />
    </TableStateProvider>
  );
};
