'use client';

import { useState } from 'react';
import { IconButton, Alert, CircularProgress, Tooltip } from '@mui/material';
import { Dialog, DialogTitle, DialogContent, Button } from '@czi-sds/components';
import { Replay as ReplayIcon } from '@mui/icons-material';
import { Job, SyncerStatus, SyncerRerunResponse } from '../types';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

// Processors that support syncer re-run
const SYNCER_SUPPORTED_PROCESSORS = ['aretomo3', 'denoiset'];

interface RerunSyncerButtonProps {
  job: Job;
  syncerStatus?: SyncerStatus | null;
  onRerun?: () => void;
  variant?: 'icon' | 'button';
}

export const RerunSyncerButton: React.FC<RerunSyncerButtonProps> = ({
  job,
  syncerStatus,
  onRerun,
  variant = 'icon',
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Determine visibility based on requirements:
  // - For running jobs: only show if syncer stopped unexpectedly
  // - For completed/failed jobs: show unless syncer is currently running
  const isRunning = ['Running', 'Pending'].includes(job.status);
  const isCompleted = ['Completed', 'Failed'].includes(job.status);
  const supportssyncer = job.processor && SYNCER_SUPPORTED_PROCESSORS.includes(job.processor);
  const syncerIsRunning = syncerStatus?.status === 'running';

  let shouldShow = false;
  if (supportssyncer) {
    if (isRunning) {
      // Show only if syncer stopped unexpectedly
      shouldShow = syncerStatus?.can_rerun ?? false;
    } else if (isCompleted) {
      // Show for completed/failed jobs, but not if syncer is currently running
      shouldShow = !syncerIsRunning;
    }
  }

  if (!shouldShow) {
    return null;
  }

  const handleOpen = (event: React.MouseEvent) => {
    const target = event.currentTarget as HTMLElement;
    target.blur();

    requestAnimationFrame(() => {
      setModalOpen(true);
      setError(null);
      setSuccess(false);
    });
  };

  const handleClose = () => {
    setModalOpen(false);
    setError(null);
    setSuccess(false);
  };

  const handleRerun = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = `${DJANGO_URL}${POST_API.RERUN_SYNCER.replace(':jobId', String(job.job.id))}`;
      const response = await postResource(url, {});
      const data: SyncerRerunResponse = await response.json();

      if (data.success) {
        setSuccess(true);
        setTimeout(() => {
          handleClose();
          if (onRerun) onRerun();
        }, 1500);
      } else {
        setError(data.error || 'Failed to re-run syncer');
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const tooltipText = isRunning ? 'Re-run syncer (stopped unexpectedly)' : 'Re-run syncer to sync outputs';

  return (
    <>
      {variant === 'icon' ? (
        <Tooltip title={tooltipText}>
          <IconButton size="small" onClick={handleOpen} color="primary" sx={{ padding: '4px' }}>
            <ReplayIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ) : (
        <Button onClick={handleOpen} sdsType="secondary" sdsStyle="square" startIcon={<ReplayIcon />}>
          Re-run Syncer
        </Button>
      )}

      <Dialog open={modalOpen} onClose={handleClose} sdsSize="s">
        <DialogTitle title={`Re-run Syncer: ${job.jobName}`} onClose={handleClose} />
        <DialogContent>
          {success ? (
            <Alert severity="success">Syncer started successfully!</Alert>
          ) : (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                This will start a new syncer process to sync output files from the cluster to the database.
              </Alert>

              {isRunning && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  The job is still running but the syncer appears to have stopped. Re-running will resume output
                  synchronization.
                </Alert>
              )}

              {isCompleted && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Job ID: <strong>{job.job.id}</strong>
                  <br />
                  Processor: <strong>{job.processor}</strong>
                  <br />
                  Session: <strong>{job.session || 'N/A'}</strong>
                </Alert>
              )}

              {!!error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
                <Button onClick={handleClose} disabled={loading} sdsType="secondary" sdsStyle="minimal">
                  Cancel
                </Button>
                <Button
                  onClick={handleRerun}
                  disabled={loading}
                  sdsType="primary"
                  sdsStyle="square"
                  startIcon={loading ? <CircularProgress size={20} /> : undefined}
                >
                  {loading ? 'Starting...' : 'Re-run Syncer'}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
