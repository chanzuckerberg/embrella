'use client';

import { Box, Typography, Paper, Skeleton } from '@mui/material';
import { Table, TableHeader, TableRow, CellHeader, CellComponent } from '@czi-sds/components';
import { TableBody } from '@mui/material';
import { Button } from '@czi-sds/components';
import { useRouter } from 'next/navigation';
import { JobStatusBadge } from '@app/processing/jobs/monitor/components/JobStatusBadge';
import type { JobStatus } from '@app/processing/jobs/monitor/types';

interface RecentJob {
  jobId: string;
  jobName: string;
  status: string;
  submittedAt: string | null;
  duration: string | null;
  cluster: string;
  user: string;
}

interface RecentJobsTableProps {
  jobs: RecentJob[];
  isLoading?: boolean;
}

export const RecentJobsTable = ({ jobs, isLoading }: RecentJobsTableProps) => {
  const router = useRouter();

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
          Your Most Recent Jobs
        </Typography>
        <Button
          sdsType="secondary"
          sdsStyle="outline"
          size="small"
          onClick={() => router.push('/processing/jobs/logs')}
        >
          View All
        </Button>
      </Box>

      <Paper elevation={1}>
        {isLoading ? (
          <Box sx={{ p: 2 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} variant="text" height={48} sx={{ mb: 1 }} />
            ))}
          </Box>
        ) : jobs.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">No recent jobs found</Typography>
          </Box>
        ) : (
          <Table>
            <TableHeader>
              <CellHeader>Job ID</CellHeader>
              <CellHeader>Job Name</CellHeader>
              <CellHeader>User</CellHeader>
              <CellHeader>Status</CellHeader>
              <CellHeader>Submitted</CellHeader>
              <CellHeader>Duration</CellHeader>
              <CellHeader>Cluster</CellHeader>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.jobId}>
                  <CellComponent>
                    <span style={{ fontFamily: 'monospace' }}>{job.jobId}</span>
                  </CellComponent>
                  <CellComponent>
                    <span style={{ fontWeight: 500 }}>{job.jobName}</span>
                  </CellComponent>
                  <CellComponent>{job.user}</CellComponent>
                  <CellComponent>
                    <JobStatusBadge status={job.status as JobStatus} />
                  </CellComponent>
                  <CellComponent>{formatDate(job.submittedAt)}</CellComponent>
                  <CellComponent>
                    <span style={{ fontFamily: 'monospace' }}>{job.duration || '-'}</span>
                  </CellComponent>
                  <CellComponent>{job.cluster}</CellComponent>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
};
