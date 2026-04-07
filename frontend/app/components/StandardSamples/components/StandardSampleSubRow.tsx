import { Link, Table, TableBody, TableHead, TableRow } from '@mui/material';
import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { useGridDetailDialog } from '@app/components/GridsView/context/GridDetailDialogContext';
import { StyledTableCell, StyledHeaderCell } from '@app/common/components/EntityTable/EntityTable';
import { GridBoxChildGrid } from '@app/components/GridInventory/GridBoxesView/types';
import { STANDARD_SAMPLE_SUB_COLUMN_DEFS, STANDARD_SAMPLE_SUB_COLUMN_IDS } from '../constants/subColumns';

interface StandardSampleSubRowProps {
  grids: GridBoxChildGrid[];
}

export const StandardSampleSubRow = ({ grids }: StandardSampleSubRowProps) => {
  const { openGridDetail } = useGridDetailDialog();

  const table = useReactTable<GridBoxChildGrid>({
    data: grids,
    columns: STANDARD_SAMPLE_SUB_COLUMN_DEFS,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => String(row.id),
  });

  if (grids.length === 0) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>No standard grids for this specimen</span>;
  }

  return (
    <Table size="small" sx={{ tableLayout: 'fixed', minWidth: 900 }}>
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
            {row.getVisibleCells().map((cell) => {
              const meta = cell.column.columnDef.meta as { align?: string } | undefined;
              const isNameCol = cell.column.id === STANDARD_SAMPLE_SUB_COLUMN_IDS.NAME;

              return (
                <StyledTableCell
                  key={cell.id}
                  width={cell.column.columnDef.size}
                  sx={meta?.align ? { textAlign: meta.align } : undefined}
                >
                  {isNameCol ? (
                    <Link component="button" onClick={() => openGridDetail(row.original.id)} sx={{ textAlign: 'left' }}>
                      {row.original.name}
                    </Link>
                  ) : (
                    flexRender(cell.column.columnDef.cell, cell.getContext())
                  )}
                </StyledTableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
