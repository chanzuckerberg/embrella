import { useState, useCallback } from 'react';
import { patchResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { parseApiError } from '@app/common/utils/api/errorHandling';

interface UpdateGridBoxData {
  grid_box_id: number;
  name?: string;
  color?: string;
  numbering?: string;
}

interface UpdateGridBoxResponse {
  success: boolean;
  message: string;
  grid_box: {
    id: number;
    name: string;
    color: string;
    color_display: string;
    numbering: string;
    numbering_display: string;
    position_in_puck: number;
    max_grids: number;
  };
}

interface UseUpdateGridBoxResult {
  updateGridBox: (data: UpdateGridBoxData) => Promise<UpdateGridBoxResponse | null>;
  isUpdating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useUpdateGridBox = (): UseUpdateGridBoxResult => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const updateGridBox = async (data: UpdateGridBoxData): Promise<UpdateGridBoxResponse | null> => {
    setIsUpdating(true);
    setError(null);

    try {
      // Build the URL by replacing grid_box_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.UPDATE_GRID_BOX).replace(
        'grid_box_id',
        data.grid_box_id.toString()
      );

      const payload: Record<string, unknown> = {};
      if (data.name !== undefined) payload.name = data.name;
      if (data.color !== undefined) payload.color = data.color;
      if (data.numbering !== undefined) payload.numbering = data.numbering;

      const response = await patchResource(url, payload);

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, 'Failed to update grid box'));
      }
    } catch (err) {
      let errorMessage = 'An error occurred while updating grid box';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsUpdating(false);
    }
  };

  return {
    updateGridBox,
    isUpdating,
    error,
    clearError,
  };
};
