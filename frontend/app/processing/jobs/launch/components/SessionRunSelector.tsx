'use client';

import { useEffect, useMemo, useState } from 'react';
import { Alert, Box, TextField, Typography } from '@mui/material';
import { AutocompleteOptionBasic, Button } from '@czi-sds/components';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { calculateNextRunName } from '../utils/runNumbers';
import { SessionFormDialog } from '@app/sessions/new/tem/components/SessionFormDialog';
import { CreatedSession } from '@app/sessions/new/tem/types';
import { SessionDetails } from './SessionDetails';

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
  planType: string; // e.g. 'aretomo3', 'denoise', 'copick'
}

export const SessionRunSelector = ({ onChange, disabled = false, planType }: SessionRunSelectorProps) => {
  const [sessions, setSessions] = useState<MsiSessionData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSession, setSelectedSession] = useState<SessionOption | undefined>(undefined);
  const [runName, setRunName] = useState<string>('');
  const [runNameError, setRunNameError] = useState<string>('');
  const [existingRuns, setExistingRuns] = useState<string[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchResource(`${DJANGO_URL}${API.MSI_SESSIONS}`);

      if (!response.ok) {
        throw new Error('Failed to fetch sessions');
      }

      // Sorted newest first by the server
      const data: { sessions: { name: string }[] } = await response.json();
      const sessionsData: MsiSessionData[] = (data.sessions || []).map(({ name }) => ({
        name,
        run_numbers: [], // Not needed since we're using text input
      }));
      setSessions(sessionsData);
      return sessionsData;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error fetching sessions');
      return [];
    } finally {
      setLoading(false);
    }
  };

  // Fetch sessions on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async data fetch on mount
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
        const response = await fetchResource(
          `${DJANGO_URL}${API.PLAN_RUNS}?session_name=${encodeURIComponent(selectedSession.session.name)}&plan_type=${encodeURIComponent(planType)}`
        );

        if (response.ok) {
          const data = await response.json();
          const sessionData = data.sessions?.[0];
          const runNumbers: string[] = sessionData?.run_numbers || [];
          const formattedRuns = runNumbers.map((num: string) => `run${num}`);
          setExistingRuns(formattedRuns);

          const nextRunName = calculateNextRunName(runNumbers);
          setRunName(nextRunName);
          setRunNameError('');
          onChange({
            sessionName: selectedSession.session.name,
            runName: nextRunName,
            isValid: true,
          });
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

  // Handle new session creation from dialog
  const handleSessionCreated = async (createdSession: CreatedSession) => {
    setShowCreateDialog(false);
    const updatedSessions = await fetchSessions();
    // Auto-select the newly created session
    const newSession = updatedSessions.find((s) => s.name === createdSession.name);
    if (newSession) {
      const option: SessionOption = { name: newSession.name, session: newSession };
      setSelectedSession(option);
    }
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

      <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1 }}>
        <Box sx={{ flex: 1 }}>
          <DropdownSelect
            topLabel="MSI Session:"
            topLabelClass="!mb-[8px]"
            value={selectedSession}
            options={sessionOptions}
            onChange={handleSessionChange}
            disabled={disabled || loading}
          />
        </Box>
        <Button sdsType="secondary" sdsStyle="minimal" onClick={() => setShowCreateDialog(true)} disabled={disabled}>
          + New Session
        </Button>
      </Box>

      {selectedSession && (
        <Box sx={{ mt: 2 }}>
          <SessionDetails key={selectedSession.session.name} sessionName={selectedSession.session.name} />
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
        <Alert severity="info" sx={{ mt: 2 }}>
          No sessions available.{' '}
          <Button sdsType="secondary" sdsStyle="minimal" onClick={() => setShowCreateDialog(true)}>
            Create a TEM session
          </Button>{' '}
          to get started.
        </Alert>
      )}

      <SessionFormDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleSessionCreated}
      />
    </Box>
  );
};
