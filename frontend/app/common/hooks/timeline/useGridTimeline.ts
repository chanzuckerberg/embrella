import { useQuery } from '@tanstack/react-query';
import { DJANGO_URL, API } from '@app/common/constants/api';
import type { TimelineEntry } from '@app/common/types/timeline';

/**
 * Grid history, newest first. Always refetched on mount so it reflects edits made in the dialog.
 */
export const useGridTimeline = (gridId: number | null) =>
  useQuery({
    queryKey: ['grid-timeline', gridId],
    queryFn: async (): Promise<TimelineEntry[]> => {
      const response = await fetch(`${DJANGO_URL}${API.GRID_TIMELINE.replace('grid_id', String(gridId))}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch grid timeline');
      }

      return response.json();
    },
    enabled: gridId !== null,
    staleTime: 0,
  });
