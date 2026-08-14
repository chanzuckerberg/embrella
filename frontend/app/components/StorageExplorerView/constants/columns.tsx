import { Box, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { ColumnDef } from '@tanstack/react-table';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { EntityDataTypes } from '@app/common/types/tableState';
import { formatDate } from '@app/common/utils/format';

import { StatusCell } from '../components/StatusCell';
import { StorageSessionData } from '../types';
import { statusLabel } from './statusLabels';

/**
 * Column ids double as the backend's `sort` values, so they must match the keys
 * of `table_sort_fields` in processes/viewsets.py.
 */
export const STORAGE_COLUMN_IDS = {
  SESSION: 'session',
  OWNER: 'owner',
  USER: 'user',
  PROJECT: 'project',
  SIZE: 'size',
  RUNS: 'runs',
  LAST_MODIFIED: 'lastModified',
  STATUS: 'status',
};

const row = (data: EntityDataTypes): StorageSessionData => data as StorageSessionData;

export const STORAGE_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: STORAGE_COLUMN_IDS.SESSION,
    accessorFn: (data) => row(data).sessionName,
    cell: ({ row: tableRow }) => {
      const { sessionName, registered } = row(tableRow.original);
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
          <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {sessionName}
          </Typography>
          {!registered && (
            <Tooltip title="Not tracked in Embrella — no MSI session record matches this folder name">
              <Box sx={{ display: 'flex', flexShrink: 0 }}>
                <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="yellow" />
              </Box>
            </Tooltip>
          )}
        </Box>
      );
    },
    enableSorting: true,
    header: 'MSI Session',
    size: 200,
  },
  {
    id: STORAGE_COLUMN_IDS.OWNER,
    accessorFn: (data) => row(data).fsOwner || '-',
    enableSorting: true,
    header: 'File Owner',
    size: 130,
  },
  {
    id: STORAGE_COLUMN_IDS.USER,
    accessorFn: (data) => row(data).user?.fullName ?? '-',
    enableSorting: true,
    header: 'Session User',
    size: 130,
  },
  {
    id: STORAGE_COLUMN_IDS.PROJECT,
    accessorFn: (data) => row(data).project?.name ?? '-',
    enableSorting: true,
    header: 'Project',
    size: 140,
  },
  {
    id: STORAGE_COLUMN_IDS.SIZE,
    accessorFn: (data) => row(data).totalSizeDisplay,
    enableSorting: true,
    header: 'Size',
    size: 110,
  },
  {
    id: STORAGE_COLUMN_IDS.RUNS,
    accessorFn: (data) => String(row(data).runCount),
    cell: ({ row: tableRow }) => {
      const { runCount, softwareCount } = row(tableRow.original);
      return (
        <Box>
          <Typography variant="body2">
            {runCount} {runCount === 1 ? 'run' : 'runs'}
          </Typography>
          {/* "software" is its own plural. */}
          <Typography variant="caption" color="text.secondary">
            {softwareCount} software
          </Typography>
        </Box>
      );
    },
    enableSorting: true,
    header: 'Contents',
    size: 110,
  },
  {
    id: STORAGE_COLUMN_IDS.LAST_MODIFIED,
    accessorFn: (data) => {
      const { lastModified } = row(data);
      return lastModified ? formatDate(lastModified) : '-';
    },
    enableSorting: true,
    header: 'Last Modified',
    size: 120,
  },
  {
    id: STORAGE_COLUMN_IDS.STATUS,
    accessorFn: (data) => statusLabel(row(data).status),
    cell: ({ row: tableRow }) => {
      const session = row(tableRow.original);
      return (
        <StatusCell
          status={session.status}
          label={`session ${session.sessionName}`}
          // One prefix per software folder: a session's data is not under a
          // single directory, so one judgement covers several.
          pathPrefixes={[...new Set(session.runs.map((run) => run.softwarePathPrefix))]}
          totalSizeDisplay={session.totalSizeDisplay}
          directoryCount={session.directoryCount}
        />
      );
    },
    // Not a stored column on the aggregate, so the backend cannot order by it.
    enableSorting: false,
    header: 'Status',
    size: 110,
  },
];
