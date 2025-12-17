'use client';

import { useEffect, useState } from 'react';
import { Alert, Box, CircularProgress, List, ListItem, ListItemIcon, ListItemText, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import { API, DJANGO_URL } from '@app/common/constants/api';

interface DependencyCheckerProps {
  pipeInPlanId: number | null;
  procRunId: number | null;
  onDependenciesChecked?: (dependenciesMet: boolean) => void;
}

export const DependencyChecker: React.FC<DependencyCheckerProps> = ({
  pipeInPlanId,
  procRunId,
  onDependenciesChecked,
}) => {
  const [loading, setLoading] = useState(false);
  const [dependenciesMet, setDependenciesMet] = useState<boolean | null>(null);
  const [missingDependencies, setMissingDependencies] = useState<string[]>([]);
  const [hasDependencies, setHasDependencies] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkDependencies = async () => {
      if (!pipeInPlanId || !procRunId) {
        setDependenciesMet(null);
        setMissingDependencies([]);
        setHasDependencies(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const url = `${DJANGO_URL}${API.PIPELINE_CHECK_DEPENDENCIES}?pipe_in_plan_id=${pipeInPlanId}&proc_run_id=${procRunId}`;
        const response = await fetch(url, {
          credentials: 'include',
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to check dependencies');
        }

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.error || 'Failed to check dependencies');
        }

        setDependenciesMet(data.dependencies_met);
        setMissingDependencies(data.missing_dependencies || []);
        setHasDependencies(data.has_dependencies || false);

        // Notify parent component
        if (onDependenciesChecked) {
          onDependenciesChecked(data.dependencies_met);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error checking dependencies');
        setDependenciesMet(null);
        setMissingDependencies([]);
        setHasDependencies(false);
      } finally {
        setLoading(false);
      }
    };

    checkDependencies();
  }, [pipeInPlanId, procRunId, onDependenciesChecked]);

  if (!pipeInPlanId || !procRunId) {
    return null;
  }

  if (loading) {
    return (
      <Box display="flex" alignItems="center" sx={{ mt: 2 }}>
        <CircularProgress size={20} sx={{ mr: 1 }} />
        <Typography variant="body2" color="text.secondary">
          Checking dependencies...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        <Typography variant="body2">{error}</Typography>
      </Alert>
    );
  }

  if (dependenciesMet === true && hasDependencies) {
    return (
      <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mt: 2 }}>
        <Typography variant="body2">
          <strong>All dependencies met</strong> - Ready to submit job
        </Typography>
      </Alert>
    );
  }

  if (dependenciesMet === false && missingDependencies.length > 0) {
    return (
      <Alert severity="warning" icon={<WarningIcon />} sx={{ mt: 2 }}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          Missing dependencies:
        </Typography>
        <List dense disablePadding>
          {missingDependencies.map((dep, index) => (
            <ListItem key={index} disablePadding sx={{ py: 1 }}>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <ErrorIcon color="warning" fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary={dep}
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'text.secondary',
                }}
              />
            </ListItem>
          ))}
        </List>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Please ensure required processing steps are completed before submitting this job.
        </Typography>
      </Alert>
    );
  }

  return null;
};
