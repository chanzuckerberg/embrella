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
  enabled?: boolean;
  pollIntervalMs?: number;
}

/** Job log tail from GET /logs: polls while active, and refetches on each state change. */
export function useDatasetLogs(
  id: number,
  { state, enabled = true, pollIntervalMs = DEFAULT_LOG_POLL_INTERVAL_MS }: DatasetLogsOptions = {}
) {
  const active = isActiveJobState(state);
  const query = useQuery<JobLogs>({
    queryKey: depositionKeys.logs(id),
    queryFn: () => fetchDatasetLogs(id),
    enabled,
    refetchInterval: active ? pollIntervalMs : false,
  });

  const { refetch } = query;
  const previous = useRef({ id, state, enabled, active });
  useEffect(() => {
    const prev = previous.current;
    previous.current = { id, state, enabled, active };
    // useQuery already covers mount, dataset change, and enabling.
    if (!enabled || !prev.enabled || prev.id !== id || prev.state === state) return;
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
  }, [id, state, enabled, active, refetch]);

  return query;
}
