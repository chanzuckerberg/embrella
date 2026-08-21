import { Table, TableBody, TableHead, TableRow } from '@mui/material';
import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';

import { StyledHeaderCell, StyledTableCell } from '@app/common/components/EntityTable/EntityTable';

import { SESSION_RUN_COLUMN_DEFS } from '../constants/runColumns';
import { SessionRunRow } from '../types';

interface SoftwareRunsSubRowProps {
  runs: SessionRunRow[];
}

/** Leaf tier: the runs behind one software label, newest first. */
export const SoftwareRunsSubRow = ({ runs }: SoftwareRunsSubRowProps) => {
  const table = useReactTable<SessionRunRow>({
    data: runs,
    columns: SESSION_RUN_COLUMN_DEFS,
    getCoreRowModel: getCoreRowModel(),
    // Already namespaced as "run-<pk>" by the API.
    getRowId: (row) => row.id,
  });

  if (runs.length === 0) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>No runs for this software</span>;
  }

  return (
    <Table size="small" sx={{ tableLayout: 'fixed', minWidth: 480 }}>
      <TableHead>
        <TableRow>
          {table.getFlatHeaders().map((header) => (
            <StyledHeaderCell key={header.id} width={header.column.columnDef.size}>
              {flexRender(header.column.columnDef.header, header.getContext())}
            </StyledHeaderCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {table.getRowModel().rows.map((row) => (
          <TableRow key={row.id} sx={{ '&:last-child td': { borderBottom: 0 } }}>
            {row.getVisibleCells().map((cell) => (
              <StyledTableCell key={cell.id} width={cell.column.columnDef.size}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </StyledTableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
