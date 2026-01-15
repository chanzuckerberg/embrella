import { ColumnDef } from '@tanstack/react-table';
import { Checkbox, Chip, Box } from '@mui/material';
import { Job } from '../types';
import { JobStatusBadge } from '../components/JobStatusBadge';
import { CancelJobButton } from '../components/CancelJobButton';
import { RerunSyncerButton } from '../components/RerunSyncerButton';

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

export const JOB_COLUMN_IDS = {
  SELECT: 'select',
  JOB_ID: 'jobId',
  JOB_NAME: 'jobName',
  WORKFLOW_TYPE: 'workflowType',
  USER: 'user',
  STATUS: 'status',
  TIME: 'time',
  CLUSTER: 'cluster',
  PARTITION: 'partition',
  NODES: 'nodes',
  ACTIONS: 'actions',
};

export const JOB_COLUMN_DEFS: ColumnDef<Job>[] = [
  {
    id: JOB_COLUMN_IDS.SELECT,
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllPageRowsSelectedHandler()}
        sx={{ padding: 0 }}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        disabled={!row.getCanSelect()}
        onChange={row.getToggleSelectedHandler()}
        sx={{ padding: 0 }}
      />
    ),
    enableSorting: false,
    enableHiding: false,
    size: 40,
  },
  {
    id: JOB_COLUMN_IDS.JOB_ID,
    accessorFn: (row) => row.job.id,
    header: 'Job ID',
    cell: ({ getValue }) => <span style={{ fontFamily: 'monospace' }}>{getValue() as string}</span>,
    enableSorting: true,
    size: 80,
  },
  {
    id: JOB_COLUMN_IDS.JOB_NAME,
    accessorKey: 'jobName',
    header: 'Job Name',
    cell: ({ getValue }) => <span style={{ fontWeight: 500 }}>{getValue() as string}</span>,
    size: 225,
    meta: { maxWidth: 350 },
  },
  {
    id: JOB_COLUMN_IDS.WORKFLOW_TYPE,
    accessorKey: 'isWorkflowLaunched',
    header: 'Source',
    cell: ({ getValue }) => {
      const isWorkflow = getValue() as boolean;
      return (
        <Chip
          label={isWorkflow ? 'Workflow' : 'Manual'}
          size="small"
          color={isWorkflow ? 'primary' : 'default'}
          sx={{ fontWeight: 500, fontSize: '0.75rem' }}
        />
      );
    },
    size: 100,
    enableHiding: true,
  },
  {
    id: JOB_COLUMN_IDS.USER,
    accessorKey: 'user',
    header: 'User',
    size: 180,
  },
  {
    id: JOB_COLUMN_IDS.TIME,
    accessorKey: 'timeUsed',
    header: 'Time',
    cell: ({ getValue, row }) => {
      const timeUsed = formatSlurmTime(getValue() as string);
      const timeLeft = formatSlurmTime(row.original.timeLeft);
      return (
        <Box sx={{ fontFamily: 'monospace', lineHeight: 1.4 }}>
          <div>{timeUsed}</div>
          {timeLeft !== 'N/A' && <div style={{ color: '#666', fontSize: '0.85em' }}>{timeLeft} left</div>}
        </Box>
      );
    },
    size: 110,
  },
  {
    id: JOB_COLUMN_IDS.CLUSTER,
    accessorKey: 'cluster',
    header: 'Cluster',
    cell: ({ getValue }) => (
      <span
        style={{
          fontWeight: 600,
          color: getValue() === 'czii' ? '#6E4FF9' : '#9c27b0',
          textTransform: 'uppercase',
        }}
      >
        {getValue() as string}
      </span>
    ),
    size: 65,
  },
  {
    id: JOB_COLUMN_IDS.PARTITION,
    accessorKey: 'partition',
    header: 'Partition',
    size: 100,
  },
  {
    id: JOB_COLUMN_IDS.NODES,
    accessorKey: 'nodes',
    header: 'Nodes',
    size: 45,
  },
  {
    id: JOB_COLUMN_IDS.STATUS,
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const status = getValue() as Job['status'];
      return <JobStatusBadge status={status} />;
    },
    size: 130,
  },
  {
    id: JOB_COLUMN_IDS.ACTIONS,
    header: '',
    cell: ({ row }) => {
      const job = row.original;
      return (
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <RerunSyncerButton job={job} syncerStatus={job.syncerStatus} />
          <CancelJobButton job={job} />
        </Box>
      );
    },
    enableSorting: false,
    size: 60,
  },
];
