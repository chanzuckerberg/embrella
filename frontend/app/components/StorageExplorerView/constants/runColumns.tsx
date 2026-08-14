import { Tooltip, Typography } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { formatDate } from '@app/common/utils/format';

import { StatusCell } from '../components/StatusCell';
import { StorageRunRow } from '../types';
import { statusLabel } from './statusLabels';

/**
 * Leaf tier: the run directories under one software folder.
 */
export const STORAGE_RUN_COLUMN_DEFS: ColumnDef<StorageRunRow>[] = [
  {
    id: 'run',
    accessorFn: (run) => run.run.name,
    cell: ({ row }) => (
      // The absolute path is what you need to find this run in All Paths or on
      // the cluster, and it is far too long for a cell.
      <Tooltip title={row.original.pathPrefix}>
        <Typography variant="body2">{row.original.run.name}</Typography>
      </Tooltip>
    ),
    header: 'Run',
    size: 160,
  },
  {
    id: 'totalSize',
    accessorFn: (run) => run.totalSizeDisplay,
    header: 'Size',
    size: 110,
  },
  {
    id: 'fileCount',
    accessorFn: (run) => run.fileCount.toLocaleString(),
    header: 'Files',
    size: 100,
  },
  {
    id: 'directoryCount',
    accessorFn: (run) => run.directoryCount.toLocaleString(),
    header: 'Directories',
    size: 110,
  },
  {
    id: 'lastModified',
    accessorFn: (run) => (run.lastModified ? formatDate(run.lastModified) : '-'),
    header: 'Last Modified',
    size: 120,
  },
  {
    id: 'status',
    accessorFn: (run) => statusLabel(run.status),
    cell: ({ row }) => (
      <StatusCell
        status={row.original.status}
        label={`run ${row.original.run.name}`}
        pathPrefixes={[row.original.pathPrefix]}
        totalSizeDisplay={row.original.totalSizeDisplay}
        directoryCount={row.original.directoryCount}
        pathPrefix={row.original.pathPrefix}
        decidedAtPrefix={row.original.decidedAtPrefix}
      />
    ),
    header: 'Status',
    size: 110,
  },
];
