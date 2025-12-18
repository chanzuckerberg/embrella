import { Chip } from '@mui/material';
import { JobStatus, JOB_STATUS_LABELS, JOB_STATUS_COLORS } from '../types';

interface JobStatusBadgeProps {
  status: JobStatus;
}

export const JobStatusBadge: React.FC<JobStatusBadgeProps> = ({ status }) => {
  const label = JOB_STATUS_LABELS[status] || status;
  const color = JOB_STATUS_COLORS[status] || '#9e9e9e';

  return (
    <Chip
      label={label}
      size="small"
      sx={{
        backgroundColor: color,
        color: '#fff',
        fontWeight: 600,
        fontSize: '0.75rem',
        height: '24px',
      }}
    />
  );
};
