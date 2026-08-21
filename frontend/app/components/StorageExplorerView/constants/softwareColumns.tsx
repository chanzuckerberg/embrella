import { ColumnDef } from '@tanstack/react-table';

import { formatDate } from '@app/common/utils/format';

import { StatusCell } from '../components/StatusCell';
import { StorageSoftwareGroup } from '../types';
import { statusLabel } from './statusLabels';

/**
 * Middle tier: one row per on-disk software folder within a session.
 */
export const STORAGE_SOFTWARE_COLUMN_DEFS: ColumnDef<StorageSoftwareGroup>[] = [
  {
    id: 'software',
    accessorFn: (group) => group.software,
    header: 'Software',
    size: 160,
  },
  {
    id: 'totalSize',
    accessorFn: (group) => group.totalSizeDisplay,
    header: 'Size',
    size: 110,
  },
  {
    id: 'runCount',
    accessorFn: (group) => `${group.runCount} ${group.runCount === 1 ? 'run' : 'runs'}`,
    header: 'Runs',
    size: 100,
  },
  {
    id: 'directoryCount',
    accessorFn: (group) => group.directoryCount.toLocaleString(),
    header: 'Directories',
    size: 110,
  },
  {
    id: 'lastModified',
    accessorFn: (group) => (group.lastModified ? formatDate(group.lastModified) : '-'),
    header: 'Last Modified',
    size: 120,
  },
  {
    id: 'status',
    accessorFn: (group) => statusLabel(group.status),
    cell: ({ row }) => (
      <StatusCell
        status={row.original.status}
        label={`${row.original.software} for this session`}
        pathPrefixes={[row.original.pathPrefix]}
        totalSizeDisplay={row.original.totalSizeDisplay}
        directoryCount={row.original.directoryCount}
        pathPrefix={row.original.pathPrefix}
      />
    ),
    header: 'Status',
    size: 110,
  },
];
