'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchDataset, pushDataset, submitDataset } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset, JobState } from '../types';

const ACTIVE_STATES: JobState[] = ['prep_submitted', 'prep_running', 'push_submitted', 'push_running'];

export const isActiveJobState = (state?: JobState | null): boolean => !!state && ACTIVE_STATES.includes(state);

/**
 * Live view of a dataset's submission: polls while a prep/push job is running and exposes
 * submit (prep) and push mutations that refresh the dataset + submissions list on completion.
 */
export function useSubmitFlow(initial: Dataset) {
  const queryClient = useQueryClient();
  const id = initial.id;

  const query = useQuery<Dataset>({
    queryKey: depositionKeys.dataset(id),
    queryFn: () => fetchDataset(id),
    initialData: initial,
    // Poll only while a job is in flight; stop once it reaches a terminal state.
    refetchInterval: (q) => (isActiveJobState(q.state.data?.job?.state) ? 4000 : false),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(id) });
    queryClient.invalidateQueries({ queryKey: depositionKeys.submissions() });
  };

  const submit = useMutation({ mutationFn: () => submitDataset(id), onSuccess: refresh });
  const push = useMutation({ mutationFn: () => pushDataset(id), onSuccess: refresh });

  return { dataset: query.data ?? initial, submit, push };
}
