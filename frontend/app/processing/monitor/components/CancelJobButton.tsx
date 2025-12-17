'use client';

import { useState, useContext, useEffect } from 'react';
import { UserContext } from '@app/common/context/UserProvider';
import { IconButton, Alert, CircularProgress, TextField } from '@mui/material';
import { Dialog, DialogTitle, DialogContent, Button } from '@czi-sds/components';
import { Cancel as CancelIcon } from '@mui/icons-material';
import { Job } from '../types';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

interface CancelJobButtonProps {
  job: Job;
  onCancel?: () => void;
}

type ModalMode = 'cancel' | 'ssh_setup' | null;

export const CancelJobButton: React.FC<CancelJobButtonProps> = ({ job, onCancel }) => {
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [password, setPassword] = useState('');

  // Get username from UserContext and extract the part before @ if it's an email
  const user = useContext(UserContext);
  const username = user?.username ? (user.username.includes('@') ? user.username.split('@')[0] : user.username) : '';

  // Debug logging
  useEffect(() => {
    console.log('Modal mode changed:', modalMode);
  }, [modalMode]);

  const handleOpen = (event: React.MouseEvent) => {
    // Blur the button immediately to prevent aria-hidden focus conflicts
    const target = event.currentTarget as HTMLElement;
    target.blur();

    // Use requestAnimationFrame to ensure blur completes before opening dialog
    requestAnimationFrame(() => {
      setModalMode('cancel');
      setError(null);
      setSuccess(false);
    });
  };

  const handleClose = () => {
    setModalMode(null);
    setError(null);
    setSuccess(false);
    setPassword('');
  };

  const performCancel = async (usernameToUse: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await postResource(`${DJANGO_URL}${POST_API.BULK_CANCEL_JOBS}`, {
        job_ids: [job.job.id],
        cluster_id: job.cluster,
        user_id: usernameToUse,
        // No password - will use SSH key if set up
      });

      const data = await response.json();

      console.log('Cancel response:', { status: response.status, data });

      if (response.status === 403 && data.ssh_setup_required) {
        // SSH setup required - switch to SSH mode
        console.log('SSH setup required, switching to SSH mode');
        setLoading(false);
        setModalMode('ssh_setup');
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

  const handleCancel = async () => {
    await performCancel(username);
  };

  const handleSSHSetup = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const encodedPassword = btoa(password);
      const response = await postResource(`${DJANGO_URL}${POST_API.SSH_SETUP_KEY}`, {
        cluster_id: job.cluster,
        username: username,
        password: encodedPassword,
      });

      const data = await response.json();

      if (data.success && data.can_connect) {
        // SSH setup successful - switch back to cancel mode and retry
        setPassword('');
        setModalMode('cancel');
        await performCancel(username);
      } else {
        setError(data.error || data.message || 'SSH setup failed. Please try again.');
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  // Only show cancel button for running or pending jobs
  if (!['Running', 'Pending'].includes(job.status)) {
    return null;
  }

  // Render different dialog content based on mode
  const renderDialogContent = () => {
    if (modalMode === 'ssh_setup') {
      return (
        <>
          <Alert severity="info" sx={{ mb: 2 }}>
            To enable passwordless job management, we need to set up SSH key authentication for your account on the{' '}
            <strong>{job.cluster.toUpperCase()}</strong> cluster.
          </Alert>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This is a one-time setup. Please enter your credentials to continue.
          </Alert>
          {!!error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <TextField
            label="Username"
            value={username}
            disabled
            fullWidth
            margin="normal"
            variant="outlined"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !loading) {
                handleSSHSetup();
              }
            }}
            fullWidth
            margin="normal"
            variant="outlined"
            autoFocus
            disabled={loading}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            Your password will be used once to add the service user&apos;s SSH key to your authorized_keys file. It will
            not be stored.
          </Alert>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button onClick={handleClose} disabled={loading} sdsType="secondary" sdsStyle="minimal">
              Cancel
            </Button>
            <Button
              onClick={handleSSHSetup}
              disabled={loading || !password}
              sdsType="primary"
              sdsStyle="square"
              startIcon={loading ? <CircularProgress size={20} /> : undefined}
            >
              {loading ? 'Setting up...' : 'Setup SSH'}
            </Button>
          </div>
        </>
      );
    }

    // Cancel mode (default)
    return success ? (
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
          <br />
          User: <strong>{username}</strong>
        </Alert>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
          <Button onClick={handleClose} disabled={loading} sdsType="secondary" sdsStyle="minimal">
            Cancel
          </Button>
          <Button
            onClick={handleCancel}
            disabled={loading}
            sdsType="primary"
            sdsStyle="square"
            startIcon={loading ? <CircularProgress size={20} /> : undefined}
          >
            {loading ? 'Cancelling...' : 'Cancel Job'}
          </Button>
        </div>
      </>
    );
  };

  const dialogTitle = modalMode === 'ssh_setup' ? 'SSH Setup Required' : `Cancel Job: ${job.jobName}`;

  return (
    <>
      <IconButton size="small" onClick={handleOpen} color="error" title="Cancel job" sx={{ padding: '4px' }}>
        <CancelIcon fontSize="small" />
      </IconButton>

      <Dialog open={modalMode !== null} onClose={handleClose} sdsSize="s">
        <DialogTitle title={dialogTitle} onClose={handleClose} />
        <DialogContent>{renderDialogContent()}</DialogContent>
      </Dialog>
    </>
  );
};
