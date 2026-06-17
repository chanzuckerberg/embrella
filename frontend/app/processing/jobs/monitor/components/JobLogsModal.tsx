'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  Alert,
  Box,
  Typography,
  Tabs,
  Tab,
  IconButton,
  Chip,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import { Job, JobLog, SyncerLogEntry, SyncerStatus, SyncerLogsResponse } from '../types';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { RerunSyncerButton } from './RerunSyncerButton';

interface JobLogsModalProps {
  open: boolean;
  onClose: () => void;
  job: Job;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
};

// Processors that support syncers
const SYNCER_SUPPORTED_PROCESSORS = ['aretomo3', 'denoiset'];

export const JobLogsModal: React.FC<JobLogsModalProps> = ({ open, onClose, job }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobLog, setJobLog] = useState<JobLog | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  // Syncer logs state
  const [syncerLogs, setSyncerLogs] = useState<SyncerLogEntry[]>([]);
  const [syncerStatus, setSyncerStatus] = useState<SyncerStatus | null>(null);
  const [syncerLoading, setSyncerLoading] = useState(false);

  // Check if job supports syncer
  const supportsSyncer = job.processor && SYNCER_SUPPORTED_PROCESSORS.includes(job.processor);

  const fetchSyncerLogs = useCallback(async () => {
    if (!supportsSyncer) return;

    setSyncerLoading(true);
    try {
      const url = `${DJANGO_URL}${API.SYNCER_LOGS.replace(':jobId', String(job.job.id))}`;
      const response = await fetchResource(url);
      const data: SyncerLogsResponse = await response.json();

      if (data.success) {
        setSyncerLogs(data.logs);
        setSyncerStatus(data.syncer_status);
      }
    } catch (err) {
      console.error('Error fetching syncer logs:', err);
    } finally {
      setSyncerLoading(false);
    }
  }, [job.job.id, supportsSyncer]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // First, try to fetch from new PipeExecution endpoint
      const executionUrl = `${DJANGO_URL}${API.PIPELINE_EXECUTION_BY_JOB_ID.replace(':jobId', String(job.job.id))}`;

      try {
        const execResponse = await fetchResource(executionUrl);
        const execData = await execResponse.json();

        if (execData.success && execData.execution) {
          // Convert PipeExecution data to JobLog format for display
          setJobLog({
            user_id: 0, // Not available from execution
            job_name: execData.execution.pipe_name,
            advanced: false, // Not tracked in PipeExecution
            job_id: execData.execution.job_id,
            created_at: execData.execution.submitted_at || execData.execution.created_at,
            parameters: execData.execution.parameters,
            error_message: execData.execution.error_message,
            script_content: execData.execution.script_content,
            // Job execution logs
            stdout_log: execData.execution.stdout_log,
            stderr_log: execData.execution.stderr_log,
            logs_fetched_at: execData.execution.logs_fetched_at,
            log_fetch_error: execData.execution.log_fetch_error,
          });
          return;
        }
      } catch (execErr) {
        // If PipeExecution lookup fails, fall back to old JobLog system
        console.log('PipeExecution not found, falling back to JobLog:', execErr);
      }

      // Fall back to old JobLog endpoint
      const url = `${DJANGO_URL}${API.JOB_LOGS}?user_name=${encodeURIComponent(job.user)}&limit=100`;
      const response = await fetchResource(url);
      const data = await response.json();

      // Find the log entry that matches this job
      const logs: JobLog[] = data.job_logs || [];
      const matchingLog = logs.find((log) => log.job_id === String(job.job.id) || log.job_name === job.jobName);

      if (matchingLog) {
        setJobLog(matchingLog);
      } else {
        setError('No log entry found for this job');
      }
    } catch (err) {
      setError(`Error fetching logs: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  }, [job.user, job.job.id, job.jobName]);

  useEffect(() => {
    if (open && job.jobName) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- async log fetch when the modal opens
      fetchLogs();
      fetchSyncerLogs();
    }
  }, [open, job.jobName, fetchLogs, fetchSyncerLogs]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            Job Logs: {job.jobName}
            <Typography variant="caption" display="block" color="text.secondary">
              Job ID: {job.job.id} | Cluster: {job.cluster.toUpperCase()}
            </Typography>
          </Box>
          <IconButton onClick={fetchLogs} disabled={loading} size="small" title="Refresh logs">
            <RefreshIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        )}

        {!!error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && jobLog && (
          <Box>
            {/* Job metadata */}
            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                Submitted At:
              </Typography>
              <Typography variant="body2">{new Date(jobLog.created_at).toLocaleString()}</Typography>
            </Box>

            {!!jobLog.logs_fetched_at && (
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom>
                  Logs Fetched At:
                </Typography>
                <Typography variant="body2">{new Date(jobLog.logs_fetched_at).toLocaleString()}</Typography>
              </Box>
            )}

            {!!jobLog.error_message && (
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom color="error">
                  Error Message:
                </Typography>
                <Alert severity="error">
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85em' }}>
                    {jobLog.error_message}
                  </pre>
                </Alert>
              </Box>
            )}

            {!!jobLog.log_fetch_error && (
              <Box mb={2}>
                <Alert severity="warning">
                  <Typography variant="subtitle2" gutterBottom>
                    Log Fetch Error:
                  </Typography>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85em' }}>
                    {jobLog.log_fetch_error}
                  </pre>
                </Alert>
              </Box>
            )}

            {/* Tabs for different log types */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 2 }}>
              <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                <Tab label="Parameters" />
                {!!jobLog.script_content && <Tab label="SLURM Script" />}
                {!!jobLog.stdout_log && <Tab label="stdout" />}
                {!!jobLog.stderr_log && <Tab label="stderr" />}
                {!!supportsSyncer && <Tab label="Syncer Logs" />}
              </Tabs>
            </Box>

            {/* Parameters tab */}
            <TabPanel value={activeTab} index={0}>
              <Box
                sx={{
                  backgroundColor: '#f5f5f5',
                  padding: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  maxHeight: 500,
                }}
              >
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '0.85em' }}>
                  {JSON.stringify(jobLog.parameters, null, 2)}
                </pre>
              </Box>
            </TabPanel>

            {/* SLURM Script tab */}
            {!!jobLog.script_content && (
              <TabPanel value={activeTab} index={1}>
                <Box
                  sx={{
                    backgroundColor: '#f5f5f5',
                    padding: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 500,
                    border: '1px solid #ddd',
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      fontFamily: 'monospace',
                      fontSize: '0.85em',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {jobLog.script_content}
                  </pre>
                </Box>
              </TabPanel>
            )}

            {/* stdout tab */}
            {!!jobLog.stdout_log && (
              <TabPanel value={activeTab} index={jobLog.script_content ? 2 : 1}>
                <Box
                  sx={{
                    backgroundColor: '#f5f5f5',
                    padding: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 500,
                    border: '1px solid #ddd',
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      fontFamily: 'monospace',
                      fontSize: '0.85em',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {jobLog.stdout_log}
                  </pre>
                </Box>
              </TabPanel>
            )}

            {/* stderr tab */}
            {!!jobLog.stderr_log && (
              <TabPanel
                value={activeTab}
                index={
                  jobLog.script_content && jobLog.stdout_log ? 3 : jobLog.script_content || jobLog.stdout_log ? 2 : 1
                }
              >
                <Box
                  sx={{
                    backgroundColor: '#fff5f5',
                    padding: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 500,
                    border: '1px solid #ffcccc',
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      fontFamily: 'monospace',
                      fontSize: '0.85em',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#d32f2f',
                    }}
                  >
                    {jobLog.stderr_log}
                  </pre>
                </Box>
              </TabPanel>
            )}

            {/* Syncer Logs tab */}
            {!!supportsSyncer && (
              <TabPanel
                value={activeTab}
                index={1 + (jobLog.script_content ? 1 : 0) + (jobLog.stdout_log ? 1 : 0) + (jobLog.stderr_log ? 1 : 0)}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="subtitle2">
                      Syncer Status:{' '}
                      {syncerStatus?.status ? (
                        <Chip
                          label={syncerStatus.status}
                          size="small"
                          color={
                            syncerStatus.status === 'running'
                              ? 'success'
                              : syncerStatus.status === 'completed'
                                ? 'info'
                                : syncerStatus.status === 'failed'
                                  ? 'error'
                                  : 'default'
                          }
                        />
                      ) : (
                        <Chip label="Not started" size="small" />
                      )}
                    </Typography>
                    {!!syncerStatus?.last_heartbeat && (
                      <Typography variant="caption" color="text.secondary">
                        Last heartbeat: {new Date(syncerStatus.last_heartbeat).toLocaleString()}
                      </Typography>
                    )}
                  </Box>
                  <RerunSyncerButton job={job} syncerStatus={syncerStatus} onRerun={fetchSyncerLogs} variant="button" />
                </Box>

                {syncerLoading ? (
                  <Box display="flex" justifyContent="center" py={4}>
                    <CircularProgress size={24} />
                  </Box>
                ) : syncerLogs.length === 0 ? (
                  <Alert severity="info">No syncer logs available for this job.</Alert>
                ) : (
                  <Box sx={{ maxHeight: 400, overflow: 'auto', border: '1px solid #ddd', borderRadius: 1 }}>
                    <Box
                      component="table"
                      sx={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.85rem',
                        '& th, & td': {
                          textAlign: 'left',
                          padding: '8px 12px',
                          borderBottom: '1px solid #eee',
                          verticalAlign: 'top',
                        },
                        '& th': {
                          backgroundColor: '#f5f5f5',
                          fontWeight: 600,
                          position: 'sticky',
                          top: 0,
                        },
                        '& tr:hover': {
                          backgroundColor: '#fafafa',
                        },
                      }}
                    >
                      <thead>
                        <tr>
                          <th style={{ width: '140px' }}>Time</th>
                          <th style={{ width: '120px' }}>Event</th>
                          <th>Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {syncerLogs.map((log, index) => (
                          <Box
                            component="tr"
                            key={index}
                            sx={{
                              backgroundColor:
                                log.action_type === 'error'
                                  ? '#fff5f5'
                                  : log.action_type === 'warning'
                                    ? '#fffef5'
                                    : 'inherit',
                            }}
                          >
                            <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#666' }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </td>
                            <td>
                              <Chip
                                label={log.action_type.replace('_', ' ')}
                                size="small"
                                color={
                                  log.action_type === 'error'
                                    ? 'error'
                                    : log.action_type === 'warning'
                                      ? 'warning'
                                      : log.action_type === 'tomogram_created'
                                        ? 'success'
                                        : log.action_type === 'init'
                                          ? 'primary'
                                          : 'default'
                                }
                                variant="outlined"
                                sx={{ fontSize: '0.7rem' }}
                              />
                            </td>
                            <td>
                              <span>{log.message}</span>
                              {Object.keys(log.metadata).length > 0 && (
                                <Box
                                  component="span"
                                  sx={{ ml: 1, color: '#888', fontSize: '0.8rem', fontFamily: 'monospace' }}
                                >
                                  {Object.entries(log.metadata)
                                    .filter(([key]) => !['session_name', 'run_id', 'job_id'].includes(key))
                                    .map(
                                      ([key, value]) =>
                                        `${key}=${typeof value === 'object' ? JSON.stringify(value) : value}`
                                    )
                                    .join(' ')}
                                </Box>
                              )}
                            </td>
                          </Box>
                        ))}
                      </tbody>
                    </Box>
                  </Box>
                )}
              </TabPanel>
            )}
          </Box>
        )}

        {!loading && !error && !jobLog && <Alert severity="info">No log data available for this job.</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};
