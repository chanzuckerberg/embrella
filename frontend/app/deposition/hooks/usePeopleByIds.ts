import { useQuery } from '@tanstack/react-query';

import { fetchPeopleByIds } from '../services/depositionApi';
import type { Person } from '../types';

export function usePeopleByIds(ids: number[]) {
  const key = [...ids].sort((a, b) => a - b);
  return useQuery<Person[]>({
    queryKey: ['people', 'by-ids', key],
    queryFn: () => fetchPeopleByIds(ids),
    enabled: ids.length > 0,
  });
}
