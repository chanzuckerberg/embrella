import React, { Fragment } from 'react';
import { Table, CellHeader, CellComponent, TableHeader, TableRow } from '@czi-sds/components';
import { TableBody, Typography } from '@mui/material';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { flexRender, SortingState, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { METADATA_COLUMN_DEFS } from '../constants/columns';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { ComputedMetric } from '@app/common/types/metadataViz/metadataSummary';

// Component for the metrics table
interface MetricsTableProps {
  metrics: ComputedMetric[];
}


export const MetricsTable: React.FC<MetricsTableProps> = ({ metrics }) => {
    const initialSortState: SortingState = [{ desc: false, id: 'name' }];
  
    const table = useReactTable({
      data: metrics,
      columns: METADATA_COLUMN_DEFS,
      getCoreRowModel: getCoreRowModel(),
    });
  
    if (!metrics || metrics.length === 0) {
      return <Typography variant="body1">No metrics data available</Typography>;
    }
  
    return (
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
    );
  };