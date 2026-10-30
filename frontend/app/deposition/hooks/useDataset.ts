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
    refetchInterval: (query) => {
      const job = query.state.data?.job;
      return isActiveJobPhase(job?.state) ||
        (!job?.ingestion_retryable &&
          (job?.ingestion_state === 'opening_pr' ||
            (job?.state === 'completed' && job.ingestion_state === 'not_started' && !!job.ingestion_branch)))
        ? DEFAULT_DATASET_POLL_INTERVAL_MS
        : false;
    },
  });
}
