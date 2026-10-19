'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@czi-sds/components';
import { Box, Typography } from '@mui/material';

import type { JobLogs, JobLogsSource } from '../../types';
import type { SubmitPhase } from '../../submitPhases';

function logNote(source: JobLogsSource | undefined, hasLines: boolean, active: boolean, restricted: boolean): string {
  if (restricted) return 'Logs are visible to the submitter only.';
  // Only promise a retry while still polling.
  if (source === 'unavailable') {
    if (hasLines) return 'Showing the saved output; the live log is unavailable.';
    return active ? "Couldn't read the live log right now - retrying." : "Couldn't read the log.";
  }
  if (hasLines) return '';
  if (!source || source === 'none') return 'No log yet - it appears once the job starts.';
  return 'No output yet.';
}

export function SubmissionLogPanel({
  data,
  active,
  phase,
  restricted = false,
}: {
  data?: JobLogs;
  active: boolean;
  phase: SubmitPhase;
  restricted?: boolean;
}) {
  const [copyStatus, setCopyStatus] = useState<{ phase: SubmitPhase; result: 'ok' | 'fail' } | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const stick = useRef(true); // follow the tail until the user scrolls up to read earlier lines
  const text = restricted ? '' : (data?.logs ?? '');
  const lines = text.split('\n').filter(Boolean);
  useEffect(() => {
    stick.current = true;
  }, [phase]);
  // Follow the tail as it grows, including the final post-completion fetch; skip if the user scrolled up.
  useEffect(() => {
    const el = scrollRef.current;
    if (stick.current && el) el.scrollTop = el.scrollHeight;
  }, [text, phase]);
  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };
  const note = logNote(data?.source, lines.length > 0, active, restricted);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus({ phase, result: 'ok' });
    } catch {
      setCopyStatus({ phase, result: 'fail' });
    }
  };
  // Auto-dismiss only the success note; the failure note asks the user to act, so leave it up.
  useEffect(() => {
    if (copyStatus?.result !== 'ok') return;
    const timer = setTimeout(() => setCopyStatus(null), 3000);
    return () => clearTimeout(timer);
  }, [copyStatus]);
  const showCopyStatus = copyStatus?.phase === phase;
  return (
    <Box
      sx={{
        bgcolor: 'grey.900',
        borderRadius: '8px',
        height: 'var(--submission-panel-height, clamp(200px, 30dvh, 400px))',
        '@media (max-height: 800px)': { height: 'var(--submission-panel-height, clamp(180px, 28dvh, 240px))' },
        minWidth: 0,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: { xs: '12px 16px', lg: '16px 20px' },
          borderBottom: '1px solid',
          borderColor: 'grey.700',
          flexShrink: 0,
        }}
      >
        <Typography variant="body1" sx={{ color: 'grey.100', fontWeight: 700 }}>
          {phase === 'prep' ? 'Sync log (tail)' : 'Upload log (tail)'}
        </Typography>
        <Button
          sdsType="secondary"
          sdsStyle="minimal"
          size="small"
          onClick={copy}
          disabled={!lines.length}
          sx={{ color: 'grey.100', '&.Mui-disabled': { color: 'grey.500' } }}
        >
          Copy
        </Button>
      </Box>
      <Box
        ref={scrollRef}
        onScroll={onScroll}
        tabIndex={0}
        role="region"
        aria-label={phase === 'prep' ? 'Sync log output' : 'Upload log output'}
        sx={{
          p: { xs: '12px 16px', lg: '16px 20px' },
          '&:focus-visible': { outline: '2px solid', outlineColor: 'primary.light', outlineOffset: -2 },
          fontFamily: 'monospace',
          fontSize: 13,
          lineHeight: 1.8,
          color: 'grey.100',
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
          <Typography variant="caption" sx={{ color: 'grey.400' }}>
            {note}
          </Typography>
        )}
      </Box>
      {showCopyStatus && (
        <Typography role="status" variant="caption" sx={{ px: 2, pb: 1, color: 'grey.100' }}>
          {copyStatus?.result === 'ok' ? 'Log copied.' : 'Could not copy. Select the log text to copy it manually.'}
        </Typography>
      )}
    </Box>
  );
}
