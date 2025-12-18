import { ColumnDef } from '@tanstack/react-table';
import { Chip } from '@mui/material';
import { Job } from '../../monitor/types';
import { JobStatusBadge } from '../../monitor/components/JobStatusBadge';

// Note: formatSlurmTime was removed - duration column commented out until sacct integration

export const HISTORICAL_JOB_COLUMN_IDS = {
  JOB_ID: 'jobId',
  JOB_NAME: 'jobName',
  PROCESSOR: 'processor',
  SESSION: 'session',
  USER: 'user',
  STATUS: 'status',
  SUBMITTED_AT: 'submittedAt',
  DURATION: 'duration',
  ACTIONS: 'actions',
};

// Use Job type since that's what the API returns
// The view component will handle any additional fields
export const HISTORICAL_JOB_COLUMN_DEFS: ColumnDef<Job>[] = [
  {
    id: HISTORICAL_JOB_COLUMN_IDS.JOB_ID,
    accessorFn: (row) => row.job.id,
    header: 'Job ID',
    cell: ({ getValue }) => <span style={{ fontFamily: 'monospace' }}>{getValue() as string}</span>,
    enableSorting: true,
    size: 100,
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.JOB_NAME,
    accessorKey: 'jobName',
    header: 'Job Name',
    cell: ({ getValue }) => <span style={{ fontWeight: 500 }}>{getValue() as string}</span>,
    size: 225,
    meta: { maxWidth: 350 },
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.PROCESSOR,
    accessorKey: 'processor',
    header: 'Processor',
    cell: ({ getValue }) => {
      const processor = getValue() as string | null;
      return processor ? (
        <Chip
          label={processor}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ fontWeight: 500, fontSize: '0.75rem' }}
        />
      ) : (
        <span style={{ color: '#999' }}>-</span>
      );
    },
    size: 120,
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.SESSION,
    accessorKey: 'session',
    header: 'Session',
    cell: ({ getValue }) => {
      const session = getValue() as string | null;
      return session || <span style={{ color: '#999' }}>-</span>;
    },
    size: 140,
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.USER,
    accessorKey: 'user',
    header: 'User',
    size: 120,
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.STATUS,
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const status = getValue() as Job['status'];
      return <JobStatusBadge status={status} />;
    },
    size: 110,
  },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.SUBMITTED_AT,
    accessorKey: 'submittedAt',
    header: 'Submitted',
    cell: ({ getValue }) => {
      const value = getValue() as string | null;
      if (!value) return <span style={{ color: '#999' }}>-</span>;
      return new Date(value).toLocaleString();
    },
    enableSorting: true,
    size: 170,
  },
  // Duration column hidden until accurate job timing via sacct is implemented
  // {
  //   id: HISTORICAL_JOB_COLUMN_IDS.DURATION,
  //   accessorKey: 'duration',
  //   header: 'Duration',
  //   cell: ({ getValue }) => {
  //     const duration = getValue() as string | null;
  //     // Duration comes pre-formatted from the backend (e.g., "1h 30m", "5m 30s")
  //     return !duration || duration === '-' ? (
  //       <span style={{ color: '#999' }}>-</span>
  //     ) : (
  //       <span style={{ fontFamily: 'monospace' }}>{duration}</span>
  //     );
  //   },
  //   size: 100,
  // },
  {
    id: HISTORICAL_JOB_COLUMN_IDS.ACTIONS,
    header: '',
    cell: () => null, // Placeholder - will be overridden in view component
    enableSorting: false,
    size: 80,
  },
];
