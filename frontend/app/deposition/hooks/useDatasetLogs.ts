'use client';

import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchDatasetLogs } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import { isActiveJobState } from './useSubmitFlow';
import type { JobLogs, JobState } from '../types';

// Gentler than the dataset poll; /logs reads over SSH.
export const DEFAULT_LOG_POLL_INTERVAL_MS = 12000;
// Mirrors the backend's per-job read cooldown.
export const SERVER_LOG_COOLDOWN_MS = 15000;

interface DatasetLogsOptions {
  state?: JobState | null;
  phase?: 'prep' | 'push';
  enabled?: boolean;
  pollIntervalMs?: number;
}

/** Job log tail from GET /logs: polls while active, and refetches on each state change. */
export function useDatasetLogs(
  id: number,
  { state, phase, enabled = true, pollIntervalMs = DEFAULT_LOG_POLL_INTERVAL_MS }: DatasetLogsOptions = {}
) {
  let active = isActiveJobState(state);
  if (phase === 'prep') active = state === 'prep_submitted' || state === 'prep_running';
  if (phase === 'push') active = state === 'push_submitted' || state === 'push_running';
  const query = useQuery<JobLogs>({
    queryKey: depositionKeys.logs(id, phase),
    queryFn: () => fetchDatasetLogs(id, phase),
    enabled,
    refetchInterval: active ? pollIntervalMs : false,
  });

  const { refetch } = query;
  const previous = useRef({ id, state, phase, enabled, active });
  useEffect(() => {
    const prev = previous.current;
    previous.current = { id, state, phase, enabled, active };
    // useQuery already covers mount, dataset change, and enabling.
    if (!enabled || !prev.enabled || prev.id !== id || prev.phase !== phase || prev.state === state) return;
    // Interval only stops the timer; fetch on the transition itself.
    const request = refetch();
    if (!prev.active || active) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // Backend's cooldown starts after the read, so chain off it.
    request.then(() => {
      if (!cancelled) timer = setTimeout(() => refetch(), SERVER_LOG_COOLDOWN_MS);
    });
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, state, phase, enabled, active, refetch]);

  return query;
}
