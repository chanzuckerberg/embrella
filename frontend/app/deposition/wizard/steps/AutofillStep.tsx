'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Alert, Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';

import { updateSession } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useAutoFill } from '../../hooks/useAutoFill';
import { SessionMetadataCard, type SessionMeta } from '../../components/autofill/SessionMetadataCard';
import type { FieldValue } from '../../components/autofill/MetadataRow';
import { countIssues, TILTSERIES_FIELDS, TOMOGRAM_FIELDS } from '../../components/autofill/fields';
import type { Dataset } from '../../types';
import type { StepProps } from '../wizardTypes';

function toSessionMeta(dataset: Dataset): SessionMeta[] {
  return (dataset.sessions ?? []).map((s, i) => ({
    key: `sm-${s.id ?? i}`,
    id: s.id,
    sessionName: s.msi_session_name ?? '',
    aretomoRun: s.aretomo_run_name ?? '',
    tiltseries: s.tiltseries_metadata ?? {},
    tomogram: s.tomogram_metadata ?? {},
    lastAutofillAt: s.last_autofill_at ?? null,
  }));
}

function hasData(s: SessionMeta): boolean {
  return Object.keys(s.tiltseries).length > 0 || Object.keys(s.tomogram).length > 0;
}

function sessionIssues(s: SessionMeta): number {
  return countIssues(TILTSERIES_FIELDS, s.tiltseries as never) + countIssues(TOMOGRAM_FIELDS, s.tomogram as never);
}

export function AutofillStep({ dataset, reportSave, reportBlocking, readOnly: readOnlyProp }: StepProps) {
  const queryClient = useQueryClient();
  const readOnly = readOnlyProp || dataset.status !== 'draft';
  const [sessions, setSessions] = useState<SessionMeta[]>(() => toSessionMeta(dataset));
  const [activeKey, setActiveKey] = useState<string>(() => {
    const initial = toSessionMeta(dataset);
    return (initial.find((s) => s.aretomoRun) ?? initial[0])?.key ?? '';
  });

  const save = useCallback(
    async (state: SessionMeta[]) => {
      const dirty = state.filter((s) => s.id && hasData(s));
      await Promise.all(
        dirty.map((s) =>
          updateSession(s.id as number, { tiltseries_metadata: s.tiltseries, tomogram_metadata: s.tomogram })
        )
      );
      queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(dataset.id) });
    },
    [dataset.id, queryClient]
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(sessions, save, { enabled: !readOnly });
  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  // Gate the wizard's Next while any required field is still empty.
  const totalIssues = sessions.reduce((n, s) => n + sessionIssues(s), 0);
  useEffect(() => {
    reportBlocking?.(totalIssues);
  }, [totalIssues, reportBlocking]);

  const autofill = useAutoFill((session) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === session.id
          ? {
              ...s,
              tiltseries: session.tiltseries_metadata ?? {},
              tomogram: session.tomogram_metadata ?? {},
              lastAutofillAt: session.last_autofill_at ?? s.lastAutofillAt,
            }
          : s
      )
    );
  });

  const setField = (key: string, tab: 'tiltseries' | 'tomogram', fieldKey: string, value: FieldValue) => {
    setSessions((prev) => prev.map((s) => (s.key === key ? { ...s, [tab]: { ...s[tab], [fieldKey]: value } } : s)));
  };

  const active = sessions.find((s) => s.key === activeKey) ?? sessions[0];

  const attempted = useRef<Set<number>>(new Set());
  const { mutate: runAutofill } = autofill;
  useEffect(() => {
    if (readOnly || !active?.id || active.lastAutofillAt || !active.aretomoRun) return;
    if (attempted.current.has(active.id)) return;
    attempted.current.add(active.id);
    runAutofill(active.id);
  }, [active?.id, active?.lastAutofillAt, active?.aretomoRun, readOnly, runAutofill]);

  if (sessions.length === 0) {
    return <Alert severity="info">Add imaging sessions on the Sources step first.</Alert>;
  }

  const autoFillErr = autofill.isError ? (autofill.error as Error)?.message : null;

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Auto-fill pulls tilt-series and tomogram metadata from each session’s AreTomo run. Give the values a quick
        review - fill in anything marked required before continuing.
      </Typography>

      {sessions.length > 1 && (
        <ToggleButtonGroup
          exclusive
          size="small"
          value={active.key}
          onChange={(_, v: string | null) => v && setActiveKey(v)}
          sx={{ mb: 2, flexWrap: 'wrap' }}
        >
          {sessions.map((s) => {
            const issues = sessionIssues(s);
            return (
              <ToggleButton key={s.key} value={s.key} sx={{ textTransform: 'none', gap: 0.75 }}>
                {s.sessionName || 'Session'}
                {issues > 0 ? (
                  <Typography component="span" variant="caption" sx={{ color: 'error.main', fontWeight: 700 }}>
                    · {issues} to fix
                  </Typography>
                ) : (
                  <CheckCircleOutlineIcon sx={{ fontSize: 16, color: 'success.main' }} />
                )}
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>
      )}

      <SessionMetadataCard
        key={active.key}
        session={active}
        readOnly={readOnly}
        autoFilling={autofill.isPending && autofill.variables === active.id}
        autoFillError={autofill.variables === active.id ? autoFillErr : null}
        onAutoFill={() => active.id && autofill.mutate(active.id)}
        onFieldChange={(tab, fieldKey, value) => setField(active.key, tab, fieldKey, value)}
      />

      <Box sx={{ mt: 2 }}>
        {totalIssues > 0 ? (
          <Alert severity="warning">
            {totalIssues} required field{totalIssues === 1 ? '' : 's'} left across{' '}
            {sessions.filter((s) => sessionIssues(s) > 0).length} session
            {sessions.filter((s) => sessionIssues(s) > 0).length === 1 ? '' : 's'}.
          </Alert>
        ) : (
          <Alert severity="success">All required metadata is filled in.</Alert>
        )}
      </Box>
    </Box>
  );
}
