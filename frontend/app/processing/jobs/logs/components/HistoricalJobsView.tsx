'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { Box, TextField, InputAdornment } from '@mui/material';
import { Search as SearchIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { Button } from '@czi-sds/components';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { Job } from '../../monitor/types';
import { HISTORICAL_JOB_COLUMN_DEFS } from '../constants/columns';
import { HISTORICAL_JOB_FILTER_CONFIGS } from '../constants/filters';
import { JobLogsModal } from '../../monitor/components/JobLogsModal';
import { API } from '@app/common/constants/api';

const CLUSTER_ID = 'czii';

export const HistoricalJobsView: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
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

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  // Job name click handler for logs modal
  const handleJobClick = useCallback((job: Job) => {
    setSelectedJob(job);
    setLogsModalOpen(true);
  }, []);

  // Customize columns to add click handler to job name and view button
  const customColumns = useMemo(() => {
    return HISTORICAL_JOB_COLUMN_DEFS.map((col) => {
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
                onClick={() => handleJobClick(row.original)}
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
            return (
              <Button sdsType="secondary" sdsStyle="square" size="small" onClick={() => handleJobClick(row.original)}>
                View
              </Button>
            );
          },
        };
      }
      return col;
    });
  }, [handleJobClick]);

  return (
    <TableStateProvider
      initialSortState={[{ id: 'submittedAt', desc: true }]}
      initialFilterState={{ status: ['Completed', 'Failed', 'Cancelled'] }}
    >
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters
            entityFilterConfigs={HISTORICAL_JOB_FILTER_CONFIGS}
            entityFilterListApi={`${API.JOBS_FILTERLIST}?cluster_id=${CLUSTER_ID}` as API}
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
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
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

          {/* Jobs Table with default filter for historical statuses */}
          <EntityTable
            key={`${CLUSTER_ID}-${refreshKey}-${debouncedJobIdSearch}-${debouncedJobNameSearch}`}
            entityApi={(() => {
              const params = [`cluster_id=${CLUSTER_ID}`];
              if (debouncedJobIdSearch) params.push(`job_id=${debouncedJobIdSearch}`);
              if (debouncedJobNameSearch) params.push(`job_name=${debouncedJobNameSearch}`);
              return `${API.JOBS}?${params.join('&')}` as API;
            })()}
            entityApiResponseField="job"
            columnDefs={customColumns}
          />

          {/* Job Logs Modal - reuse from monitor */}
          {selectedJob && (
            <JobLogsModal open={logsModalOpen} onClose={() => setLogsModalOpen(false)} job={selectedJob} />
          )}
        </Box>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
