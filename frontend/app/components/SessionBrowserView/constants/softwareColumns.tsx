import { ColumnDef } from '@tanstack/react-table';

import { formatDate } from '@app/common/utils/date';

import { SessionSoftwareGroup } from '../types';

/**
 * Middle tier: one row per processing-software display name within a session.
 */
export const SESSION_SOFTWARE_COLUMN_DEFS: ColumnDef<SessionSoftwareGroup>[] = [
  {
    id: 'planLabel',
    accessorFn: (group) => group.planLabel,
    header: 'Software',
    size: 100,
  },
  {
    id: 'runCount',
    accessorFn: (group) => `${group.runCount} ${group.runCount === 1 ? 'run' : 'runs'}`,
    header: 'Runs',
    size: 100,
  },
  {
    id: 'latestRunAt',
    accessorFn: (group) => (group.latestRunAt ? formatDate(group.latestRunAt) : '-'),
    header: 'Latest Run',
    size: 100,
  },
];
