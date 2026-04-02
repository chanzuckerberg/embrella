import { Box } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { EntityDataTypes } from '@app/common/types/tableState';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { GridBoxData } from '../types';

export const GRID_BOX_COLUMN_IDS = {
  NAME: 'name',
  PUCK: 'puck',
  POSITION_IN_PUCK: 'positionInPuck',
  COLOR: 'color',
  GRID_COUNT: 'gridCount',
  PUCK_USER: 'puckUser',
};

export const GRID_BOX_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: GRID_BOX_COLUMN_IDS.NAME,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as GridBoxData).gridBox.name,
    enableSorting: false,
    header: 'Grid Box',
    size: 150,
  },
  {
    id: GRID_BOX_COLUMN_IDS.PUCK,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as GridBoxData).puckName ?? '-',
    enableSorting: true,
    header: 'Puck',
    size: 50,
  },
  {
    id: GRID_BOX_COLUMN_IDS.POSITION_IN_PUCK,
    accessorFn: (rowData: EntityDataTypes): string => {
      const pos = (rowData as GridBoxData).positionInPuck;
      return pos != null ? String(pos) : '-';
    },
    enableSorting: false,
    header: 'Slot',
    size: 50,
  },
  {
    id: GRID_BOX_COLUMN_IDS.GRID_COUNT,
    accessorFn: (rowData: EntityDataTypes): string => {
      const data = rowData as GridBoxData;
      return `${data.gridCount} / ${data.maxGrids}`;
    },
    enableSorting: true,
    header: 'Grids',
    size: 50,
  },
  {
    id: GRID_BOX_COLUMN_IDS.COLOR,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as GridBoxData).colorDisplay,
    cell: ({ row }) => {
      const data = row.original as GridBoxData;
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
    size: 50,
  },
  {
    id: GRID_BOX_COLUMN_IDS.PUCK_USER,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as GridBoxData).puckUser ?? '-',
    enableSorting: false,
    header: 'User',
    size: 140,
  },
];
