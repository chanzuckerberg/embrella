import { Box } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { EntityDataTypes } from '@app/common/types/tableState';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { PuckData } from '../types';

export const PUCK_COLUMN_IDS = {
  NAME: 'name',
  CANE: 'caneName',
  POSITION_IN_CANE: 'positionInCane',
  COLOR: 'color',
  GRID_BOX_COUNT: 'gridBoxCount',
  USER: 'userName',
};

export const PUCK_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: PUCK_COLUMN_IDS.NAME,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as PuckData).puck.name,
    enableSorting: false,
    header: 'Puck',
    size: 150,
  },
  {
    id: PUCK_COLUMN_IDS.CANE,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as PuckData).caneName ?? '-',
    enableSorting: true,
    header: 'Cane',
    size: 100,
  },
  {
    id: PUCK_COLUMN_IDS.POSITION_IN_CANE,
    accessorFn: (rowData: EntityDataTypes): string => {
      const pos = (rowData as PuckData).positionInCane;
      return pos != null ? String(pos) : '-';
    },
    enableSorting: false,
    header: 'Position',
    size: 50,
  },
  {
    id: PUCK_COLUMN_IDS.COLOR,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as PuckData).colorDisplay,
    cell: ({ row }) => {
      const data = row.original as PuckData;
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
  {
    id: PUCK_COLUMN_IDS.GRID_BOX_COUNT,
    accessorFn: (rowData: EntityDataTypes): string => {
      const data = rowData as PuckData;
      return `${data.gridBoxCount} / ${data.maxBoxes}`;
    },
    enableSorting: true,
    header: 'Grid Boxes',
    size: 80,
  },
  {
    id: PUCK_COLUMN_IDS.USER,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as PuckData).userName ?? '-',
    enableSorting: false,
    header: 'User',
    size: 140,
  },
];
