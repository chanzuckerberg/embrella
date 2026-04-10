import React, { useState } from 'react';
import { Box, Collapse, IconButton, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ExpandedState,
  getExpandedRowModel,
} from '@tanstack/react-table';
import { StyledTableCell, StyledHeaderCell } from '@app/common/components/EntityTable/EntityTable';
import { GridBoxData } from '@app/components/GridInventory/GridBoxesView/types';
import { GridBoxSubRow } from '@app/components/GridInventory/GridBoxesView/components/GridBoxSubRow';
import { PUCK_GRID_BOX_COLUMN_DEFS } from '../constants/gridBoxColumns';

interface PuckSubRowProps {
  gridBoxes: GridBoxData[];
}

export const PuckSubRow = ({ gridBoxes }: PuckSubRowProps) => {
  const data = gridBoxes ?? [];
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const table = useReactTable<GridBoxData>({
    data,
    columns: PUCK_GRID_BOX_COLUMN_DEFS,
    state: { expanded },
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowId: (row) => String(row.gridBox.id),
    getRowCanExpand: (row) => (row.original.grids?.length ?? 0) > 0,
  });

  if (data.length === 0) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>No grid boxes in this puck</span>;
  }

  return (
    <Table size="small" sx={{ tableLayout: 'fixed', minWidth: 600 }}>
      <TableHead>
        <TableRow>
          <StyledHeaderCell width={40} />
          {table.getFlatHeaders().map((header) => (
            <StyledHeaderCell key={header.id} width={header.column.columnDef.size}>
              {flexRender(header.column.columnDef.header, header.getContext())}
            </StyledHeaderCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {table.getRowModel().rows.map((row) => {
          const canExpand = row.getCanExpand();
          const isExpanded = row.getIsExpanded();

          return (
            <React.Fragment key={row.id}>
              <TableRow
                hover
                sx={{
                  ...(canExpand ? { cursor: 'pointer' } : {}),
                  '&:last-child td': { borderBottom: 0 },
                }}
                onClick={canExpand ? () => row.toggleExpanded() : undefined}
              >
                <StyledTableCell width={40} sx={{ px: 0.5 }}>
                  {canExpand && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        row.toggleExpanded();
                      }}
                    >
                      {isExpanded ? (
                        <KeyboardArrowDownIcon fontSize="small" />
                      ) : (
                        <KeyboardArrowRightIcon fontSize="small" />
                      )}
                    </IconButton>
                  )}
                </StyledTableCell>
                {row.getVisibleCells().map((cell) => (
                  <StyledTableCell key={cell.id} width={cell.column.columnDef.size}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </StyledTableCell>
                ))}
              </TableRow>

              {canExpand && (
                <TableRow sx={!isExpanded ? { display: 'none' } : undefined}>
                  <TableCell colSpan={table.getFlatHeaders().length + 1} sx={{ p: 0 }}>
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <Box sx={{ pl: 4, pr: 2, py: 1, bgcolor: '#f0f0f0', minWidth: 'fit-content' }}>
                        <GridBoxSubRow grids={row.original.grids ?? []} />
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          );
        })}
      </TableBody>
    </Table>
  );
};
