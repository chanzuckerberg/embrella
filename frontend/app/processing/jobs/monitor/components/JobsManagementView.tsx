'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { Box, Alert, TextField, InputAdornment } from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import { RowSelectionState } from '@tanstack/react-table';
import { Button } from '@czi-sds/components';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { BulkActionsBar } from '@app/common/components/BulkActionsBar/BulkActionsBar';
import { Job } from '../types';
import { JOB_COLUMN_DEFS } from '../constants/columns';
import { JOB_FILTER_CONFIGS } from '../constants/filters';
import { ClusterSelector } from '@app/common/components/ClusterSelector';
import { JobLogsModal } from './JobLogsModal';
import { SSHSetupModal } from '@app/common/components/SSHSetupModal';
import { CancelJobButton } from './CancelJobButton';
import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

export const JobsManagementView: React.FC = () => {
  const [selectedCluster, setSelectedCluster] = useState<'czii' | 'bruno'>('czii');
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [bulkCancelLoading, setBulkCancelLoading] = useState(false);
  const [bulkCancelError, setBulkCancelError] = useState<string | null>(null);
  const [bulkCancelSuccess, setBulkCancelSuccess] = useState(false);
  const [sshSetupModalOpen, setSSHSetupModalOpen] = useState(false);
  const [currentUsername, setCurrentUsername] = useState<string>('');
  const [sshSetupContext, setSSHSetupContext] = useState<'check_access' | 'bulk_cancel' | null>(null);
  const [jobIdSearch, setJobIdSearch] = useState<string>('');
  const [jobNameSearch, setJobNameSearch] = useState<string>('');

  // Debounced search values (for API calls)
  const [debouncedJobIdSearch, setDebouncedJobIdSearch] = useState<string>('');
  const [debouncedJobNameSearch, setDebouncedJobNameSearch] = useState<string>('');

  // Debounce job ID search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedJobIdSearch(jobIdSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [jobIdSearch]);

  // Debounce job name search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedJobNameSearch(jobNameSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [jobNameSearch]);

  // Get selected job IDs
  const selectedJobIds = useMemo(() => {
    return Object.keys(rowSelection).filter((id) => rowSelection[id]);
  }, [rowSelection]);

  // Manual refresh handler
  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
    setRowSelection({});
    setBulkCancelError(null);
    setBulkCancelSuccess(false);
  }, []);

  // Cluster change handler
  const handleClusterChange = useCallback((cluster: 'czii' | 'bruno') => {
    setSelectedCluster(cluster);
    setRowSelection({});
    setRefreshKey((prev) => prev + 1);
  }, []);

  // SSH setup required handler (called by ClusterSelector for "Check Access")
  const handleSSHSetupRequired = useCallback((cluster: 'czii' | 'bruno', username: string) => {
    setCurrentUsername(username);
    setSSHSetupContext('check_access');
    setSSHSetupModalOpen(true);
  }, []);

  // Check SSH setup and perform bulk cancel
  const performBulkCancel = useCallback(
    async (username: string) => {
      setBulkCancelLoading(true);
      setBulkCancelError(null);
      setBulkCancelSuccess(false);

      try {
        const response = await postResource(`${DJANGO_URL}${POST_API.BULK_CANCEL_JOBS}`, {
          job_ids: selectedJobIds,
          cluster_id: selectedCluster,
          user_id: username,
          // No password - will use SSH key if set up
        });

        const data = await response.json();

        console.log('Bulk cancel response:', { status: response.status, data });

        if (response.status === 403 && data.ssh_setup_required) {
          // SSH setup required for bulk cancel operation
          console.log('SSH setup required for bulk cancel, opening modal');
          setCurrentUsername(username);
          setSSHSetupContext('bulk_cancel');
          setSSHSetupModalOpen(true);
          return;
        }

        if (data.success) {
          setBulkCancelSuccess(true);
          setTimeout(() => {
            handleRefresh();
          }, 2000);
        } else {
          setBulkCancelError('Failed to cancel some jobs. Check individual results.');
        }
      } catch (err) {
        setBulkCancelError(`Error: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBulkCancelLoading(false);
      }
    },
    [selectedJobIds, selectedCluster, handleRefresh]
  );

  // Bulk cancel handler
  const handleBulkCancel = useCallback(async () => {
    if (selectedJobIds.length === 0) return;

    // Prompt for username
    const username = prompt('Enter your username:');
    if (!username) return;

    await performBulkCancel(username);
  }, [selectedJobIds, performBulkCancel]);

  // SSH setup success handler - behavior depends on context
  const handleSSHSetupSuccess = useCallback(() => {
    setSSHSetupModalOpen(false);

    // Only perform bulk cancel if that's why the modal was opened
    if (sshSetupContext === 'bulk_cancel' && currentUsername) {
      performBulkCancel(currentUsername);
    }

    // Reset context
    setSSHSetupContext(null);
  }, [sshSetupContext, currentUsername, performBulkCancel]);

  // SSH setup modal close handler
  const handleSSHSetupClose = useCallback(() => {
    setSSHSetupModalOpen(false);
    setSSHSetupContext(null);
  }, []);

  // Job name click handler for logs modal
  const handleJobNameClick = useCallback((job: Job) => {
    setSelectedJob(job);
    setLogsModalOpen(true);
  }, []);

  // Customize columns to add click handler to job name and filter out Source/Cluster columns
  const customColumns = useMemo(() => {
    return JOB_COLUMN_DEFS.filter((col) => col.id !== 'workflowType' && col.id !== 'cluster').map((col) => {
      if (col.id === 'jobName') {
        return {
          ...col,
          cell: ({ getValue, row }: { getValue: () => unknown; row: { original: Job } }) => {
            const value = getValue() as string;
            return (
              <span
                style={{
                  fontWeight: 500,
                  color: '#6E4FF9',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
                onClick={() => handleJobNameClick(row.original)}
              >
                {value}
              </span>
            );
          },
        };
      }
      if (col.id === 'actions') {
        return {
          ...col,
          cell: ({ row }: { row: { original: Job } }) => {
            const job = row.original;
            return <CancelJobButton job={job} onCancel={handleRefresh} />;
          },
        };
      }
      return col;
    });
  }, [handleJobNameClick, handleRefresh]);

  return (
    <TableStateProvider initialSortState={[{ id: 'jobId', desc: true }]}>
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters
            entityFilterConfigs={JOB_FILTER_CONFIGS}
            entityFilterListApi={`${API.JOBS_FILTERLIST}?cluster_id=${selectedCluster}` as API}
          />
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 2 }}>
            <TextField
              size="small"
              placeholder="Search Job ID"
              value={jobIdSearch}
              onChange={(e) => setJobIdSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
              fullWidth
            />
            <TextField
              size="small"
              placeholder="Search Job Name"
              value={jobNameSearch}
              onChange={(e) => setJobNameSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
              fullWidth
            />
          </Box>
        </Sidebar>
        <Box sx={{ padding: '8px 24px', '@media (max-width: 900px)': { padding: '8px' } }}>
          {/* Cluster Selector and Actions Bar */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <ClusterSelector
              value={selectedCluster}
              onChange={handleClusterChange}
              showCheckAccess={true}
              onSSHSetupRequired={handleSSHSetupRequired}
            />
            <Button
              sdsType="secondary"
              sdsStyle="square"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
            >
              Refresh
            </Button>
          </Box>

          {/* Bulk Actions */}
          {selectedJobIds.length > 0 && (
            <BulkActionsBar count={selectedJobIds.length}>
              <Button sdsType="primary" sdsStyle="square" onClick={handleBulkCancel} disabled={bulkCancelLoading}>
                {bulkCancelLoading
                  ? 'Cancelling...'
                  : `Cancel ${selectedJobIds.length} Job${selectedJobIds.length > 1 ? 's' : ''}`}
              </Button>
            </BulkActionsBar>
          )}

          {/* Bulk Cancel Feedback */}
          {!!bulkCancelError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setBulkCancelError(null)}>
              {bulkCancelError}
            </Alert>
          )}

          {bulkCancelSuccess && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setBulkCancelSuccess(false)}>
              Jobs cancelled successfully! Refreshing...
            </Alert>
          )}

          {/* Jobs Table */}
          <EntityTable
            key={`${selectedCluster}-${refreshKey}-${debouncedJobIdSearch}-${debouncedJobNameSearch}`}
            entityApi={(() => {
              const params = [`cluster_id=${selectedCluster}`];
              if (debouncedJobIdSearch) params.push(`job_id=${debouncedJobIdSearch}`);
              if (debouncedJobNameSearch) params.push(`job_name=${debouncedJobNameSearch}`);
              return `${API.JOBS}?${params.join('&')}` as API;
            })()}
            entityApiResponseField="job"
            columnDefs={customColumns}
            enableRowSelection={true}
            rowSelection={rowSelection}
            onRowSelectionChange={setRowSelection}
          />

          {/* Job Logs Modal */}
          {selectedJob && (
            <JobLogsModal open={logsModalOpen} onClose={() => setLogsModalOpen(false)} job={selectedJob} />
          )}

          {/* SSH Setup Modal */}
          <SSHSetupModal
            open={sshSetupModalOpen}
            onClose={handleSSHSetupClose}
            onSuccess={handleSSHSetupSuccess}
            cluster={selectedCluster}
            username={currentUsername}
            purpose="management"
          />
        </Box>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
