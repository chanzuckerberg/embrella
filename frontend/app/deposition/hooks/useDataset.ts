import { useQuery } from '@tanstack/react-query';

import { fetchDataset } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset } from '../types';

export function useDataset(id: number | null) {
  return useQuery<Dataset>({
    queryKey: depositionKeys.dataset(id ?? -1),
    queryFn: () => fetchDataset(id as number),
    enabled: id != null && id > 0,
  });
}
