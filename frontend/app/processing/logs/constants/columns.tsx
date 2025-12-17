import { ColumnDef } from '@tanstack/react-table';
import { Chip } from '@mui/material';
import { Job } from '../../monitor/types';
import { JobStatusBadge } from '../../monitor/components/JobStatusBadge';

/**
 * Parse SLURM time format (D-HH:MM:SS or HH:MM:SS or MM:SS) to human-readable string
 */
const formatSlurmTime = (timeStr: string | null | undefined): string => {
  if (!timeStr || timeStr === 'N/A' || timeStr === 'INVALID' || timeStr.toLowerCase() === 'invalid') return 'N/A';

  let days = 0;
  let hours = 0;
  let minutes = 0;
  let seconds = 0;

  try {
    // Handle "D-HH:MM:SS" format
    if (timeStr.includes('-')) {
      const [dayPart, timePart] = timeStr.split('-');
      days = parseInt(dayPart, 10);
      const timeParts = timePart.split(':').map((p) => parseInt(p, 10));
      if (timeParts.length === 3) {
        [hours, minutes, seconds] = timeParts;
      }
    } else {
      // Handle "HH:MM:SS" or "MM:SS" format
      const parts = timeStr.split(':').map((p) => parseInt(p, 10));
      if (parts.length === 3) {
        [hours, minutes, seconds] = parts;
      } else if (parts.length === 2) {
        [minutes, seconds] = parts;
      }
    }

    // Build human-readable string
    const components: string[] = [];
    if (days > 0) components.push(`${days}d`);
    if (hours > 0) components.push(`${hours}h`);
    if (minutes > 0) components.push(`${minutes}m`);
    if (seconds > 0 && days === 0) components.push(`${seconds}s`); // Skip seconds if showing days

    return components.length > 0 ? components.join(' ') : '0s';
  } catch {
    return 'N/A';
  }
};

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
