'use client';

import { Button } from '@czi-sds/components';
import { Box, Typography } from '@mui/material';

import type { JobLogs, JobLogsSource } from '../../types';
import type { SubmitPhase } from '../../submitPhases';

function logNote(source: JobLogsSource | undefined, hasLines: boolean, active: boolean): string {
  // Only promise a retry while still polling.
  if (source === 'unavailable') {
    if (hasLines) return 'Showing the saved output; the live log is unavailable.';
    return active ? "Couldn't read the live log right now - retrying." : "Couldn't read the log.";
  }
  if (hasLines) return '';
  if (!source || source === 'none') return 'No log yet - it appears once the job starts.';
  return 'No output yet.';
}

export function SubmissionLogPanel({ data, active, phase }: { data?: JobLogs; active: boolean; phase: SubmitPhase }) {
  const text = data?.logs ?? '';
  const lines = text.split('\n').filter(Boolean);
  const note = logNote(data?.source, lines.length > 0, active);
  const copy = () => {
    if (text && navigator.clipboard) navigator.clipboard.writeText(text).catch(() => undefined);
  };
  return (
    <Box
      sx={{
        bgcolor: 'grey.900',
        borderRadius: 2,
        p: 2,
        height: 320,
        minWidth: 0,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, flexShrink: 0 }}>
        <Typography variant="body2" sx={{ color: 'grey.100', fontWeight: 700 }}>
          {phase === 'prep' ? 'Sync log (tail)' : 'Upload log (tail)'}
        </Typography>
        <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={copy} disabled={!lines.length}>
          Copy
        </Button>
      </Box>
      <Box
        sx={{
          fontFamily: 'monospace',
          fontSize: 12,
          color: 'grey.300',
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
          overflow: 'auto',
          minHeight: 0,
          flex: 1,
        }}
      >
        {lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
        {note && (
          <Typography variant="caption" sx={{ color: 'grey.500' }}>
            {note}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
