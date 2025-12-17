'use client';

import { useContext } from 'react';
import { Box, Typography, Container, Alert } from '@mui/material';
import { UserContext } from '@app/common/context/UserProvider';
import { useDashboardData } from './hooks/useDashboardData';
import { QuickActions } from './components/QuickActions';
import { RecentJobsTable } from './components/RecentJobsTable';
import { RecentSessionsTable } from './components/RecentSessionsTable';

export const DashboardView = () => {
  const user = useContext(UserContext);
  const { recentJobs, isLoading, error } = useDashboardData();

  return (
    <Container maxWidth="lg" sx={{ py: 4, mt: -8 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 5 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Welcome{user?.username ? `, ${user.username}` : ''}
        </Typography>
        <Typography variant="body1" color="text.secondary"></Typography>
      </Box>

      {/* Error Alert */}
      {!!error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}

      {/* Quick Actions */}
      <Box sx={{ mb: 5 }}>
        <QuickActions />
      </Box>

      {/* Recent Jobs Table */}
      <Box sx={{ mb: 5 }}>
        <RecentJobsTable jobs={recentJobs} isLoading={isLoading} />
      </Box>

      {/* Recent Sessions Table */}
      <Box sx={{ mb: 5 }}>
        <RecentSessionsTable isLoading={isLoading} />
      </Box>
    </Container>
  );
};
