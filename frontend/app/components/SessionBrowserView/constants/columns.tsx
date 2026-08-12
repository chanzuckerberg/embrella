import { Box, Chip } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { EntityDataTypes } from '@app/common/types/tableState';
import { formatDate } from '@app/common/utils/date';
import { GridNameCell } from '@app/components/GridsView/components/GridNameCell';

import { SessionOverviewData } from '../types';

/**
 * Column ids double as the backend's `sort` values, so they have to match the
 * keys of `table_sort_fields` in tem/viewsets.py
 */
export const SESSION_COLUMN_IDS = {
  SESSION: 'name',
  PROJECT: 'project',
  GRID: 'grid',
  PROCESSING_SOFTWARE: 'processingSoftware',
  USER: 'user',
  LAST_RUN_AT: 'lastRunAt',
};

export const SESSION_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: SESSION_COLUMN_IDS.SESSION,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as SessionOverviewData).session.name,
    enableSorting: true,
    header: 'Session',
    size: 140,
  },
  {
    id: SESSION_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as SessionOverviewData).project?.name ?? '-',
    enableSorting: true,
    header: 'Project',
    size: 160,
  },
  {
    id: SESSION_COLUMN_IDS.GRID,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as SessionOverviewData).grid?.name ?? '-',
    cell: ({ row }) => {
      const { grid } = row.original as SessionOverviewData;
      return grid ? <GridNameCell gridId={grid.id} name={grid.name} /> : '-';
    },
    enableSorting: true,
    header: 'Grid',
    size: 140,
  },
  {
    id: SESSION_COLUMN_IDS.PROCESSING_SOFTWARE,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as SessionOverviewData).processingSoftware.join(', ') || '-',
    cell: ({ row }) => {
      const { processingSoftware } = row.original as SessionOverviewData;
      if (processingSoftware.length === 0) return '-';
      return (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {processingSoftware.map((label) => (
            <Chip key={label} label={label} size="small" variant="outlined" />
          ))}
        </Box>
      );
    },
    enableSorting: true,
    header: 'Processing Software',
    size: 220,
  },
  {
    id: SESSION_COLUMN_IDS.USER,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as SessionOverviewData).user?.fullName ?? '-',
    enableSorting: true,
    header: 'User',
    size: 140,
  },
  {
    id: SESSION_COLUMN_IDS.LAST_RUN_AT,
    accessorFn: (rowData: EntityDataTypes): string => {
      const { lastRunAt } = rowData as SessionOverviewData;
      return lastRunAt ? formatDate(lastRunAt) : '-';
    },
    enableSorting: true,
    header: 'Last Run At',
    size: 120,
  },
];
