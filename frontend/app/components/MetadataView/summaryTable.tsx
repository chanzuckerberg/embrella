import React, { Fragment } from 'react';
import { Table, CellHeader, CellComponent, TableHeader, TableRow } from '@czi-sds/components';
import { TableBody, Card, CardContent, Divider, Typography, Paper } from '@mui/material';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { flexRender, SortingState, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { METADATA_COLUMN_DEFS } from './constants/columns';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';

interface SummaryTableProps {
  data: MetadataSummaryResponse;
}

export const SummaryTable = ({ data }: SummaryTableProps) => {
  const table = useReactTable({
    data: data.computed_metrics,
    columns: METADATA_COLUMN_DEFS,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!data || data.computed_metrics.length === 0) {
    return <Typography variant="body1">No metrics data available</Typography>;
  }
  const initialSortState: SortingState = [{ desc: false, id: 'name' }];

  return (
    <div style={{ marginTop: 4 }}>
      <Paper sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 1, mt: 1 }}>
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Session:</strong> {data.session_name}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Run:</strong> {data.run_number}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Total number of Tomograms:</strong> {data.num_tomograms}
            </Typography>
            <Divider sx={{ my: 3 }} />
            <Typography variant="body1" sx={{ mb: 1, wordBreak: 'break-all' }}>
              <strong>Data Collection Path:</strong> {data.data_collection_directory}
            </Typography>
            <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
              <strong>Aretomo3 Processing Path:</strong> {data.aretomo3_processing_directory}
            </Typography>
          </CardContent>
        </Card>

        {data.computed_metrics && data.computed_metrics.length > 0 ? (
          <div style={{ marginTop: 4 }}>
            <TableStateProvider initialSortState={initialSortState}>
              <Fragment>
                <FilterableTableMain>
                  <TableWrapper>
                    <Table>
                      <TableHeader>
                        {table.getFlatHeaders().map((header) => (
                          <CellHeader
                            key={header.id}
                            active={false}
                            direction={header.column.getCanSort() ? 'asc' : undefined}
                            hideSortIcon={!header.column.getCanSort()}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </CellHeader>
                        ))}
                      </TableHeader>
                      <TableBody>
                        {table.getRowModel().rows.map((row) => (
                          <TableRow key={row.id}>
                            {row.getVisibleCells().map((cell) => (
                              <CellComponent key={cell.id}>
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                              </CellComponent>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableWrapper>
                </FilterableTableMain>
              </Fragment>
            </TableStateProvider>
          </div>
        ) : (
          <Typography variant="body1" className="mt-4">
            No metrics data available
          </Typography>
        )}
      </Paper>
    </div>
  );
};
