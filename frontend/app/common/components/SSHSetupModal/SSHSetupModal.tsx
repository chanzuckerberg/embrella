'use client';

import { useState, useEffect } from 'react';
import { TextField, Alert, CircularProgress, Box, Typography } from '@mui/material';
import { Dialog, DialogTitle, DialogContent, Button } from '@czi-sds/components';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

interface SSHSetupModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  cluster: 'czii' | 'bruno';
  defaultUsername?: string;
  purpose?: 'submission' | 'management';
}

export const SSHSetupModal: React.FC<SSHSetupModalProps> = ({
  open,
  onClose,
  onSuccess,
  cluster,
  defaultUsername = '',
  purpose = 'submission',
}) => {
  const [username, setUsername] = useState(defaultUsername);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUsername(defaultUsername);
  }, [defaultUsername, open]);

  const handleSubmit = async () => {
    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError('Username is required');
      return;
    }
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const encodedPassword = btoa(password);

      const response = await postResource(`${DJANGO_URL}${POST_API.SSH_SETUP_KEY}`, {
        cluster_id: cluster,
        username: trimmedUsername,
        password: encodedPassword,
      });

      const data = await response.json();

      if (data.success && data.can_connect) {
        // SSH setup successful
        setPassword('');
        onSuccess();
        onClose();
      } else {
        // SSH setup failed
        setError(data.error || data.message || 'SSH setup failed. Please try again.');
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setPassword('');
      setError(null);
      onClose();
    }
  };

  const purposeText = purpose === 'management' ? 'job management' : 'job submission';

  return (
    <Dialog open={open} onClose={handleClose} sdsSize="s">
      <DialogTitle title="SSH Setup Required" onClose={handleClose} />
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            To enable passwordless {purposeText}, we need to set up SSH key authentication for your account on the{' '}
            <strong>{cluster.toUpperCase()}</strong> cluster.
          </Typography>

          <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
            This is a one-time setup. Please enter your credentials to continue:
          </Typography>

          <TextField
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
            autoFocus
            disabled={loading}
            helperText={`Your username on the ${cluster.toUpperCase()} cluster`}
          />

          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !loading) {
                handleSubmit();
              }
            }}
            fullWidth
            margin="normal"
            variant="outlined"
            disabled={loading}
          />

          {!!error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          <Alert severity="info" sx={{ mt: 2 }}>
            Your password will be used once to add the service user&apos;s SSH key to your authorized_keys file. It will
            not be stored.
          </Alert>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button onClick={handleClose} disabled={loading} sdsType="secondary" sdsStyle="minimal">
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={loading || !password || !username.trim()}
              sdsType="primary"
              sdsStyle="solid"
              startIcon={loading ? <CircularProgress size={20} /> : undefined}
            >
              {loading ? 'Setting up...' : 'Setup SSH'}
            </Button>
          </div>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
