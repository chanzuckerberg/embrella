'use client';

import { useState, useContext, useEffect, useCallback } from 'react';
import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Box, Alert, Link } from '@mui/material';
import { UserContext } from '@app/common/context/UserProvider';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

interface ClusterSelectorProps {
  value: 'czii' | 'bruno';
  onChange: (cluster: 'czii' | 'bruno') => void;
  showCheckAccess?: boolean;
  onSSHSetupRequired?: (cluster: 'czii' | 'bruno', username: string) => void;
  disabled?: boolean;
  recheckTrigger?: number; // Increment this to trigger a re-check of SSH access
}

export const ClusterSelector: React.FC<ClusterSelectorProps> = ({
  value,
  onChange,
  showCheckAccess = false,
  onSSHSetupRequired,
  disabled = false,
  recheckTrigger,
}) => {
  const user = useContext(UserContext);
  const [checkingAccess, setCheckingAccess] = useState(false);
  const [accessCheckResult, setAccessCheckResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value as 'czii' | 'bruno');
  };

  const handleCheckAccess = useCallback(async () => {
    if (!user?.username) {
      setAccessCheckResult({
        success: false,
        message: 'User not authenticated',
      });
      return;
    }

    setCheckingAccess(true);
    setAccessCheckResult(null);

    try {
      const response = await postResource(`${DJANGO_URL}${API.SSH_CHECK_SETUP}`, {
        cluster_id: value,
      });

      const data = await response.json();

      if (data.setup_required) {
        // Notify parent to open SSH setup modal
        const username = user.username.includes('@') ? user.username.split('@')[0] : user.username;
        if (onSSHSetupRequired) {
          onSSHSetupRequired(value, username);
        }
      } else {
        // Show success message
        setAccessCheckResult({
          success: true,
          message: `SSH access configured for ${data.username} on ${value.toUpperCase()}`,
        });
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
          setAccessCheckResult(null);
        }, 5000);
      }
    } catch (err) {
      setAccessCheckResult({
        success: false,
        message: `Error checking access: ${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setCheckingAccess(false);
    }
  }, [user, value, onSSHSetupRequired]);

  // Trigger a re-check when recheckTrigger changes
  useEffect(() => {
    if (recheckTrigger !== undefined && recheckTrigger > 0) {
      handleCheckAccess();
    }
  }, [recheckTrigger, handleCheckAccess]);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <FormControl size="small" sx={{ minWidth: 150 }} disabled={disabled}>
          <InputLabel id="cluster-select-label">Cluster</InputLabel>
          <Select
            labelId="cluster-select-label"
            id="cluster-select"
            value={value}
            label="Cluster"
            onChange={handleChange}
          >
            <MenuItem value="czii">CZII</MenuItem>
            <MenuItem value="bruno">Bruno</MenuItem>
          </Select>
        </FormControl>

        {showCheckAccess && (
          <Link
            component="button"
            onClick={handleCheckAccess}
            disabled={checkingAccess || disabled}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              paddingLeft: '4px',
              fontSize: '0.75rem',
              textDecoration: 'none',
              '&:hover': {
                textDecoration: 'underline',
              },
              cursor: checkingAccess || disabled ? 'default' : 'pointer',
              opacity: checkingAccess || disabled ? 0.6 : 1,
            }}
          >
            {checkingAccess ? 'Checking...' : 'Check Access'}
          </Link>
        )}
      </Box>

      {/* Access Check Feedback */}
      {!!accessCheckResult && (
        <Alert
          severity={accessCheckResult.success ? 'success' : 'error'}
          sx={{ mt: 1 }}
          onClose={() => setAccessCheckResult(null)}
        >
          {accessCheckResult.message}
        </Alert>
      )}
    </Box>
  );
};
