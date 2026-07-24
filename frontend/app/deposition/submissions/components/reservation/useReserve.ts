'use client';

import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createDataset, createDeposition } from '../../../services/depositionApi';
import { depositionKeys } from '../../../queryKeys';
import type { DatasetChoice, Mode } from './types';

export interface ReserveParams {
  mode: Mode;
  datasetChoice: DatasetChoice;
  depositionId: string;
  existingDatasetId: string;
}

export function useReserve(onDone: () => void) {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ mode, datasetChoice, depositionId, existingDatasetId }: ReserveParams): Promise<number> => {
      if (mode === 'reuse_dataset') return Number(existingDatasetId);

      if (mode === 'new') {
        const dep = await createDeposition({ title: '' });
        const ds = await createDataset({ deposition: dep.id, title: '' });
        return ds.id;
      }

      if (datasetChoice === 'existing') return Number(existingDatasetId);
      const ds = await createDataset({ deposition: Number(depositionId), title: '' });
      return ds.id;
    },
    onSuccess: (datasetId) => {
      queryClient.invalidateQueries({ queryKey: [...depositionKeys.all, 'submissions'] });
      onDone();
      router.push(`/deposition/wizard/${datasetId}`);
    },
  });
}
