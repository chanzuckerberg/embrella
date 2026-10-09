'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchDataset, pushDataset, submitDataset } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset, JobState } from '../types';

const ACTIVE_STATES: JobState[] = ['prep_submitted', 'prep_running', 'push_submitted', 'push_running'];
export const DEFAULT_SUBMIT_POLL_INTERVAL_MS = 4000;

interface SubmitFlowOptions {
  pollIntervalMs?: number;
}

export const isActiveJobState = (state?: JobState | null): boolean => !!state && ACTIVE_STATES.includes(state);

/**
 * Live view of a dataset's submission: polls while a prep/push job is running and exposes
 * submit (prep) and push mutations that refresh the dataset + submissions list once they settle.
 */
export function useSubmitFlow(
  initial: Dataset,
  { pollIntervalMs = DEFAULT_SUBMIT_POLL_INTERVAL_MS }: SubmitFlowOptions = {}
) {
  const queryClient = useQueryClient();
  const id = initial.id;

  const query = useQuery<Dataset>({
    queryKey: depositionKeys.dataset(id),
    queryFn: () => fetchDataset(id),
    initialData: initial,
    // Poll only while a job is in flight; stop once it reaches a terminal state.
    refetchInterval: (q) => (isActiveJobState(q.state.data?.job?.state) ? pollIntervalMs : false),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(id) });
    queryClient.invalidateQueries({ queryKey: depositionKeys.submissionsRoot() });
  };

  const submit = useMutation({ mutationFn: () => submitDataset(id), onSettled: refresh });
  const push = useMutation({ mutationFn: () => pushDataset(id), onSettled: refresh });

  return { dataset: query.data ?? initial, submit, push };
}
