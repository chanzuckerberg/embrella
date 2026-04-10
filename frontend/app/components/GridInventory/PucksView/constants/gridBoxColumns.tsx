import { Box } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { GridBoxData } from '@app/components/GridInventory/GridBoxesView/types';

/**
 * Column defs for grid boxes rendered inside a puck sub-row.
 * Omits puck name and puck user since the parent puck is already visible.
 */
export const PUCK_GRID_BOX_COLUMN_DEFS: ColumnDef<GridBoxData, unknown>[] = [
  {
    id: 'name',
    accessorFn: (row) => row.gridBox.name,
    enableSorting: false,
    header: 'Grid Box',
    size: 150,
  },
  {
    id: 'positionInPuck',
    accessorFn: (row) => (row.positionInPuck != null ? String(row.positionInPuck) : '-'),
    enableSorting: false,
    header: 'Slot',
    size: 50,
  },
  {
    id: 'gridCount',
    accessorFn: (row) => `${row.gridCount} / ${row.maxGrids}`,
    enableSorting: false,
    header: 'Grids',
    size: 60,
  },
  {
    id: 'color',
    accessorFn: (row) => row.colorDisplay,
    cell: ({ row }) => {
      const data = row.original;
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 14,
              height: 14,
              borderRadius: '50%',
              bgcolor: `#${data.color}`,
              border: '1px solid #ccc',
              flexShrink: 0,
            }}
          />
          {data.colorDisplay}
        </Box>
      );
    },
    enableSorting: false,
    header: 'Color',
    size: 100,
  },
];
