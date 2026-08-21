import { ColumnDef } from '@tanstack/react-table';

import { formatDate } from '@app/common/utils/format';

import { SessionRunRow } from '../types';

/**
 * The individual runs under one software label.
 */
export const SESSION_RUN_COLUMN_DEFS: ColumnDef<SessionRunRow>[] = [
  {
    id: 'run',
    accessorFn: (row) => row.run.name,
    header: 'Run',
    size: 138,
  },
  {
    id: 'planName',
    accessorFn: (row) => row.planName,
    header: 'Plan',
    size: 100,
  },
  {
    id: 'createdAt',
    accessorFn: (row) => formatDate(row.createdAt),
    header: 'Created',
    size: 100,
  },
];
