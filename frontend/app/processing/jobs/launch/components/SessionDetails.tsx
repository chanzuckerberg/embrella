'use client';

import { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Accordion, AccordionDetails, AccordionHeader } from '@czi-sds/components';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { SessionSummary } from '@app/sessions/new/tem/components/SessionSummary';
import type { CreatedSession } from '@app/sessions/new/tem/types';

/**
 * Collapsed accordion under the session picker with the same content as the
 * created-session dialog. Mount with key={sessionName} so state resets per session.
 */
export const SessionDetails = ({ sessionName }: { sessionName: string }) => {
  const [session, setSession] = useState<CreatedSession | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchResource(`${DJANGO_URL}${API.MSI_SESSIONS}${encodeURIComponent(sessionName)}/`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((data: CreatedSession) => {
        if (!cancelled) setSession(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionName]);

  return (
    <Box sx={{ mt: 1, mb: 5 }} data-testid="session-details">
      <Accordion id={`session-details-${sessionName}`} togglePosition="left">
        <AccordionHeader subtitle={session?.session_plan_name}>Session details</AccordionHeader>
        <AccordionDetails>
          {session && <SessionSummary session={session} />}
          {!session && (
            <Typography variant="body2" color="text.secondary">
              {failed ? 'Could not load session details.' : 'Loading…'}
            </Typography>
          )}
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};
