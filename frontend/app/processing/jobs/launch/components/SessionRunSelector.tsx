'use client';

import { useEffect, useMemo, useState } from 'react';
import { Alert, Box, TextField, Typography } from '@mui/material';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import { DJANGO_URL } from '@app/common/constants/api';
import { AutocompleteOptionBasic } from '@czi-sds/components';

interface MsiSessionData {
  name: string;
  run_numbers: string[]; // Array of existing run numbers like ["001", "002"]
}

interface SessionOption extends AutocompleteOptionBasic {
  session: MsiSessionData;
}

export interface SessionRunSelection {
  sessionName: string | null;
  runName: string | null;
  isValid: boolean; // Added to track validation state
}

interface SessionRunSelectorProps {
  onChange: (selection: SessionRunSelection) => void;
  disabled?: boolean;
}

export const SessionRunSelector = ({ onChange, disabled = false }: SessionRunSelectorProps) => {
  const [sessions, setSessions] = useState<MsiSessionData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSession, setSelectedSession] = useState<SessionOption | undefined>(undefined);
  const [runName, setRunName] = useState<string>('');
  const [runNameError, setRunNameError] = useState<string>('');
  const [existingRuns, setExistingRuns] = useState<string[]>([]);

  // Fetch sessions on mount - just get all MSI sessions
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${DJANGO_URL}/workflow/get_msi_session_list`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch sessions');
        }

        const data = await response.json();
        // Transform session_names array to sessions array format
        const sessionsData = (data.session_names || []).map((name: string) => ({
          name,
          run_numbers: [], // Not needed since we're using text input
        }));
        setSessions(sessionsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error fetching sessions');
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  // Convert sessions to dropdown options
  const sessionOptions = useMemo(() => sessions.map((session) => ({ name: session.name, session })), [sessions]);

  // Fetch existing runs when session is selected
  useEffect(() => {
    const fetchExistingRuns = async () => {
      if (!selectedSession) {
        setExistingRuns([]);
        return;
      }

      try {
        const response = await fetch(
          `${DJANGO_URL}/workflow/aretomo3_params?session_name=${encodeURIComponent(selectedSession.session.name)}`,
          {
            credentials: 'include',
          }
        );

        if (response.ok) {
          const data = await response.json();
          const sessionData = data.sessions?.[0];
          if (sessionData?.run_numbers) {
            // Format existing runs as "run001", "run002", etc.
            const sortedRunNumbers = sessionData.run_numbers.sort(
              (a: string, b: string) =>
                parseInt(a.match('[0-9]+$')?.[0] || '0') - parseInt(b.match('[0-9]+$')?.[0] || '0')
            );
            const formattedRuns = sortedRunNumbers.map((num: string) => `run${num}`);
            setExistingRuns(formattedRuns);
            const newRunNum = String(parseInt(sortedRunNumbers[sortedRunNumbers.length - 1]) + 1).padStart(3, '0');
            // Fake a run name change event:
            handleRunNameChange({ target: { value: `run${newRunNum}` } } as React.ChangeEvent<HTMLInputElement>);
          }
        }
      } catch (err) {
        console.error('Error fetching existing runs:', err);
      }
    };

    fetchExistingRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSession]);

  // Validate run name
  const validateRunName = (name: string): string => {
    if (!name) {
      return 'Run name is required';
    }

    // Check format: must be "run" followed by digits
    const runPattern = /^run\d{3}$/;
    if (!runPattern.test(name)) {
      return 'Run name must be in format "run###" (e.g., run001, run002)';
    }

    // Check if run already exists
    if (existingRuns.includes(name)) {
      return 'Run already exists for this session';
    }

    return '';
  };

  // Handle session selection
  const handleSessionChange = (sessionOption: SessionOption | undefined) => {
    setSelectedSession(sessionOption);
    setRunName(''); // Reset run name when session changes
    setRunNameError('');

    onChange({
      sessionName: sessionOption?.session.name ?? null,
      runName: null,
      isValid: false,
    });
  };

  // Handle run name input
  const handleRunNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setRunName(value);

    // Validate the run name
    const error = validateRunName(value);
    setRunNameError(error);

    const isValid = !error && !!value && !!selectedSession;

    onChange({
      sessionName: selectedSession?.session.name ?? null,
      runName: value || null,
      isValid,
    });
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        2. Select Session and Run Name
      </Typography>

      {!!error && (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <DropdownSelect
        topLabel="MSI Session:"
        topLabelClass="!mb-[8px]"
        value={selectedSession}
        options={sessionOptions}
        onChange={handleSessionChange}
        disabled={disabled || loading || sessions.length === 0}
      />

      {selectedSession && (
        <Box sx={{ mt: 2 }}>
          <TextField
            label="Processing Run Name"
            placeholder="run001"
            value={runName}
            onChange={handleRunNameChange}
            disabled={disabled}
            fullWidth
            error={!!runNameError}
            helperText={runNameError || 'Enter a unique run name in format "run###" (e.g., run001, run002)'}
          />
          {existingRuns.length > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Existing runs: {existingRuns.join(', ')}
            </Typography>
          )}
        </Box>
      )}

      {sessions.length === 0 && !loading && !error && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          No sessions available. Create a TEM session first before launching workflows.
        </Alert>
      )}
    </Box>
  );
};
