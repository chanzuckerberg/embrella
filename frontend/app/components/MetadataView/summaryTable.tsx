import React, { Fragment } from 'react';
import { Table, CellHeader, CellComponent, TableHeader, TableRow } from '@czi-sds/components';
import { TableBody } from '@mui/material';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { flexRender } from '@tanstack/react-table';
import { METADATA_COLUMN_DEFS } from './constants/columns';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { Card, CardContent, Divider } from '@mui/material';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import { SortingState } from '@tanstack/react-table';

export const SummaryTable = ({ data }) => {
  if (!data || data.length === 0) {
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
                        {METADATA_COLUMN_DEFS.map((col) => (
                          <CellHeader
                            key={col.id}
                            active={false}
                            direction={col.enableSorting ? 'asc' : undefined}
                            hideSortIcon={!col.enableSorting}
                            onClick={col.enableSorting ? () => {} : undefined}
                          >
                            {flexRender(col.header, {})}
                          </CellHeader>
                        ))}
                      </TableHeader>
                      <TableBody>
                        {data.computed_metrics.map((row, i) => (
                          <TableRow key={i}>
                            {METADATA_COLUMN_DEFS.map((col) => (
                              <CellComponent key={col.id}>
                                {col.cell
                                  ? col.cell({ getValue: () => row[col.accessorKey as keyof typeof row] })
                                  : row[col.accessorKey as keyof typeof row]}
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
