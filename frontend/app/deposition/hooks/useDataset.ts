import { useQuery } from '@tanstack/react-query';

import { fetchDataset } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset } from '../types';
import { isActiveJobPhase } from '../submitPhases';

const DEFAULT_DATASET_POLL_INTERVAL_MS = 4000;

export function useDataset(id: number | null) {
  return useQuery<Dataset>({
    queryKey: depositionKeys.dataset(id ?? -1),
    queryFn: () => fetchDataset(id as number),
    enabled: id != null && id > 0,
    // Keep metadata screens current if the owner navigates back during preparation.
    refetchInterval: (query) =>
      isActiveJobPhase(query.state.data?.job?.state) ? DEFAULT_DATASET_POLL_INTERVAL_MS : false,
  });
}
