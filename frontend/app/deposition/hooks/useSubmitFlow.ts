'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { cancelDatasetUpload, pushDataset, submitDataset } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';

/** Submission actions; useDataset owns the live dataset query and polling. */
export function useSubmitFlow(id: number, depositionId: number) {
  const queryClient = useQueryClient();
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(id) }),
      queryClient.invalidateQueries({ queryKey: depositionKeys.deposition(depositionId) }),
      queryClient.invalidateQueries({ queryKey: depositionKeys.submissionsRoot() }),
    ]);
  const submit = useMutation({ mutationFn: () => submitDataset(id), onSettled: refresh });
  const push = useMutation({ mutationFn: () => pushDataset(id), onSettled: refresh });
  const cancel = useMutation({ mutationFn: (jobId: string) => cancelDatasetUpload(id, jobId), onSettled: refresh });
  return { submit, push, cancel };
}
