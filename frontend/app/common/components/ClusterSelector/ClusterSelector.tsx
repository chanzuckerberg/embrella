'use client';

import { useState, useContext, useEffect, useCallback } from 'react';
import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Box, Alert, Link } from '@mui/material';
import { UserContext } from '@app/common/context/UserProvider';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';
import { useClusters } from '@app/common/hooks/useClusters';

interface ClusterSelectorProps {
  value: string;
  onChange: (cluster: string) => void;
  allowedClusters?: string[]; // Restrict choices; omit to offer every active cluster
  showCheckAccess?: boolean;
  onSSHSetupRequired?: (cluster: string, username: string) => void;
  disabled?: boolean;
  recheckTrigger?: number; // Increment this to trigger a re-check of SSH access
}

export const ClusterSelector: React.FC<ClusterSelectorProps> = ({
  value,
  onChange,
  allowedClusters,
  showCheckAccess = false,
  onSSHSetupRequired,
  disabled = false,
  recheckTrigger,
}) => {
  const user = useContext(UserContext);
  const { data: clusters = [] } = useClusters();
  const [checkingAccess, setCheckingAccess] = useState(false);
  const [accessCheckResult, setAccessCheckResult] = useState<{ success: boolean; message: string } | null>(null);

  // Offer only allowed clusters, e.g. allowedClusters=['hpc-a'] hides 'hpc-b'.
  const options = allowedClusters ? clusters.filter((c) => allowedClusters.includes(c.cluster_id)) : clusters;

  const clusterName = useCallback(
    (clusterId: string) => clusters.find((c) => c.cluster_id === clusterId)?.name ?? clusterId,
    [clusters]
  );

  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value);
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
        // Notify parent to open SSH setup modal. The backend returns the
        // persisted cluster username when one exists (so we can pre-fill
        // it for re-setup), or null for first-time setup.
        const resolvedUsername = typeof data.username === 'string' ? data.username : '';
        if (onSSHSetupRequired) {
          onSSHSetupRequired(value, resolvedUsername);
        }
      } else {
        // Show success message
        setAccessCheckResult({
          success: true,
          message: `SSH access configured for ${data.username} on ${clusterName(value)}`,
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
  }, [user, value, onSSHSetupRequired, clusterName]);

  // Re-run the async access check when the parent bumps recheckTrigger (an external signal).
  useEffect(() => {
    if (recheckTrigger !== undefined && recheckTrigger > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- async action in response to an external trigger
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
            // MUI warns on values missing from the menu (e.g. before clusters load).
            value={options.some((c) => c.cluster_id === value) ? value : ''}
            label="Cluster"
            onChange={handleChange}
          >
            {options.map((c) => (
              <MenuItem key={c.cluster_id} value={c.cluster_id}>
                {c.name}
              </MenuItem>
            ))}
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
