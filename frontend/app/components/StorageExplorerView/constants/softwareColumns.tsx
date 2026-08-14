import { ColumnDef } from '@tanstack/react-table';

import { formatDate } from '@app/common/utils/format';

import { StatusTag } from '../components/StatusTag';
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
    cell: ({ row }) => <StatusTag status={row.original.status} />,
    header: 'Status',
    size: 110,
  },
];
