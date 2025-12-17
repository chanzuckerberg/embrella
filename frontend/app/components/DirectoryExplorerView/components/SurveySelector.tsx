import { useEffect, useState } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Box,
  Typography,
  Chip,
  CircularProgress,
} from '@mui/material';

import { FilesystemSurvey } from '../types';
import { fetchSurveys } from '../api';

interface SurveySelectorProps {
  selectedSurveyId: number | null;
  onSurveyChange: (surveyId: number | null) => void;
  cluster?: string;
}

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default' | 'info'> = {
  completed: 'success',
  running: 'info',
  processing: 'info',
  pending: 'default',
  submitted: 'warning',
  failed: 'error',
};

/**
 * Dropdown selector for choosing which filesystem survey to display.
 * Defaults to the most recently completed survey.
 */
export const SurveySelector = ({ selectedSurveyId, onSurveyChange, cluster }: SurveySelectorProps) => {
  const [surveys, setSurveys] = useState<FilesystemSurvey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSurveys = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchSurveys(cluster);
        setSurveys(response.surveys);

        // Auto-select the most recent completed survey if none selected
        if (selectedSurveyId === null && response.surveys.length > 0) {
          const completedSurveys = response.surveys.filter((s) => s.status === 'completed');
          if (completedSurveys.length > 0) {
            // Sort by completed_at descending, take first
            const mostRecent = completedSurveys.sort((a, b) => {
              const dateA = a.completed_at ? new Date(a.completed_at).getTime() : 0;
              const dateB = b.completed_at ? new Date(b.completed_at).getTime() : 0;
              return dateB - dateA;
            })[0];
            onSurveyChange(mostRecent.id);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load surveys');
      } finally {
        setLoading(false);
      }
    };

    loadSurveys();
  }, [cluster, selectedSurveyId, onSurveyChange]);

  const handleChange = (event: SelectChangeEvent<number | ''>) => {
    const value = event.target.value;
    onSurveyChange(value === '' ? null : (value as number));
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={20} />
        <Typography variant="body2">Loading surveys...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Typography color="error" variant="body2">
        {error}
      </Typography>
    );
  }

  if (surveys.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No surveys available. Run a filesystem survey to begin.
      </Typography>
    );
  }

  return (
    <FormControl sx={{ minWidth: 400 }} size="small">
      <InputLabel id="survey-selector-label">Survey</InputLabel>
      <Select
        labelId="survey-selector-label"
        id="survey-selector"
        value={selectedSurveyId ?? ''}
        label="Survey"
        onChange={handleChange}
      >
        {surveys.map((survey) => (
          <MenuItem key={survey.id} value={survey.id}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {survey.base_path} (
                <span
                  style={{
                    fontWeight: 600,
                    color: survey.cluster === 'czii' ? '#6E4FF9' : '#9c27b0',
                  }}
                >
                  {survey.cluster}
                </span>
                )
              </Typography>
              <Chip label={survey.status} size="small" color={STATUS_COLORS[survey.status] || 'default'} />
              <Typography variant="caption" color="text.secondary">
                {formatDate(survey.completed_at || survey.submitted_at)}
              </Typography>
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
