import { useQuery } from '@tanstack/react-query';
import { DJANGO_URL, API } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import type { Cluster } from '@app/common/types/workflow';

// Clusters rarely change; fetch once per page load.
const STALE = Infinity;

/** Active clusters configured in the backend (stores.Cluster). */
export const useClusters = () => {
  return useQuery({
    queryKey: ['clusters'],
    queryFn: async (): Promise<Cluster[]> => {
      const response = await fetchResource(`${DJANGO_URL}${API.CLUSTERS}`);
      if (!response.ok) {
        throw new Error('Failed to fetch clusters');
      }

      const data: { clusters: Cluster[] } = await response.json();
      return data.clusters;
    },
    staleTime: STALE,
  });
};
