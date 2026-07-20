import { useQuery } from '@tanstack/react-query';

import { fetchDeposition } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Deposition } from '../types';

export function useDeposition(id: number | null) {
  return useQuery<Deposition>({
    queryKey: depositionKeys.deposition(id ?? -1),
    queryFn: () => fetchDeposition(id as number),
    enabled: id != null && id > 0,
  });
}
