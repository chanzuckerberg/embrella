import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { resetDatasetPreparation } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset } from '../types';

export function usePreparationEditing(dataset: Dataset | undefined) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const canReopen =
    !!dataset &&
    dataset.is_owner !== false &&
    (dataset.job?.state === 'prep_completed' || dataset.job?.state === 'failed');
  const { mutate, reset, status, error } = useMutation({
    mutationFn: (id: number) => resetDatasetPreparation(id),
    onSuccess: (job, id) => {
      setDialogOpen(false);
      // Unlock only after the server clears the old attempt and validation.
      queryClient.setQueryData<Dataset>(depositionKeys.dataset(id), (previous) =>
        previous ? { ...previous, status: 'draft', job } : previous
      );
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(id) }),
        queryClient.invalidateQueries({ queryKey: depositionKeys.deposition(dataset?.deposition ?? -1) }),
        queryClient.invalidateQueries({ queryKey: depositionKeys.submissionsRoot() }),
      ]);
    },
  });

  return {
    readOnly: !dataset || dataset.is_owner === false || dataset.status !== 'draft',
    canReopen,
    dialogOpen: canReopen && dialogOpen,
    preparing: status === 'pending',
    error,
    requestEdit: () => setDialogOpen(true),
    cancelEdit: () => {
      if (status === 'pending') return;
      setDialogOpen(false);
      reset();
    },
    confirmEdit: () => {
      if (canReopen && dataset && status !== 'pending') mutate(dataset.id);
    },
  };
}
