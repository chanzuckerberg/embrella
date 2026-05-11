'use client';

import { useState } from 'react';
import { IconButton, Alert, CircularProgress } from '@mui/material';
import { Dialog, DialogTitle, DialogContent, Button } from '@czi-sds/components';
import { Cancel as CancelIcon } from '@mui/icons-material';
import { Job } from '../types';
import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';
import { SSHSetupModal } from '@app/common/components/SSHSetupModal';

interface CancelJobButtonProps {
  job: Job;
  onCancel?: () => void;
}

export const CancelJobButton: React.FC<CancelJobButtonProps> = ({ job, onCancel }) => {
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [sshModalOpen, setSshModalOpen] = useState(false);
  const [sshDefaultUsername, setSshDefaultUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleOpen = (event: React.MouseEvent) => {
    // Blur the button immediately to prevent aria-hidden focus conflicts
    const target = event.currentTarget as HTMLElement;
    target.blur();

    requestAnimationFrame(() => {
      setCancelDialogOpen(true);
      setError(null);
      setSuccess(false);
    });
  };

  const handleClose = () => {
    setCancelDialogOpen(false);
    setError(null);
    setSuccess(false);
  };

  const performCancel = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await postResource(`${DJANGO_URL}${POST_API.BULK_CANCEL_JOBS}`, {
        job_ids: [job.job.id],
        cluster_id: job.cluster,
      });

      const data = await response.json();

      if (response.status === 403 && data.ssh_setup_required) {
        // Look up any persisted cluster username so the SSH setup modal
        // pre-fills the value the user previously confirmed.
        try {
          const checkResp = await postResource(`${DJANGO_URL}${API.SSH_CHECK_SETUP}`, {
            cluster_id: job.cluster,
          });
          const checkData = await checkResp.json();
          setSshDefaultUsername(typeof checkData.username === 'string' ? checkData.username : '');
        } catch (checkErr) {
          console.warn('Failed to fetch resolved cluster username:', checkErr);
          setSshDefaultUsername('');
        }
        setSshModalOpen(true);
        return;
      }

      if (data.success && data.cancelled > 0) {
        setSuccess(true);
        setTimeout(() => {
          handleClose();
          if (onCancel) onCancel();
        }, 1500);
      } else {
        setError(data.results?.[0]?.message || 'Failed to cancel job');
      }
    } catch (err) {
      setError(`Error cancelling job: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSSHSetupSuccess = async () => {
    setSshModalOpen(false);
    await performCancel();
  };

  // Only show cancel button for running or pending jobs
  if (!['Running', 'Pending'].includes(job.status)) {
    return null;
  }

  return (
    <>
      <IconButton size="small" onClick={handleOpen} color="error" title="Cancel job" sx={{ padding: '4px' }}>
        <CancelIcon fontSize="small" />
      </IconButton>

      <Dialog open={cancelDialogOpen} onClose={handleClose} sdsSize="s">
        <DialogTitle title={`Cancel Job: ${job.jobName}`} onClose={handleClose} />
        <DialogContent>
          {success ? (
            <Alert severity="success" sx={{ mt: 2 }}>
              Job {job.job.id} cancelled successfully!
            </Alert>
          ) : (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Are you sure you want to cancel this job? This action cannot be undone.
              </Alert>

              {!!error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Alert severity="info">
                Job ID: <strong>{job.job.id}</strong>
                <br />
                Cluster: <strong>{job.cluster.toUpperCase()}</strong>
              </Alert>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
                <Button onClick={handleClose} disabled={loading} sdsType="secondary" sdsStyle="minimal">
                  Cancel
                </Button>
                <Button
                  onClick={performCancel}
                  disabled={loading}
                  sdsType="primary"
                  sdsStyle="square"
                  startIcon={loading ? <CircularProgress size={20} /> : undefined}
                >
                  {loading ? 'Cancelling...' : 'Cancel Job'}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <SSHSetupModal
        open={sshModalOpen}
        onClose={() => setSshModalOpen(false)}
        onSuccess={handleSSHSetupSuccess}
        cluster={job.cluster as 'czii' | 'bruno'}
        defaultUsername={sshDefaultUsername}
        purpose="management"
      />
    </>
  );
};
