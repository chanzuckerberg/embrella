import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { patchResource } from '@app/common/queries/fetchResource';
import { MoveGridData, MoveGridResponse } from '@app/common/types/gridLogging/entities/grid';
import { parseApiError } from '@app/common/utils/api/errorHandling';

interface UseMoveGridResult {
  moveGrid: (data: MoveGridData) => Promise<MoveGridResponse | null>;
  isMoving: boolean;
  error: string | null;
  clearError: () => void;
}

export const useMoveGrid = (): UseMoveGridResult => {
  const [isMoving, setIsMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const moveGrid = async (data: MoveGridData): Promise<MoveGridResponse | null> => {
    setIsMoving(true);
    setError(null);

    try {
      // Build the URL by replacing grid_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.MOVE_GRID).replace('grid_id', data.grid_id.toString());

      const response = await patchResource(url, {
        destination_grid_box_id: data.destination_grid_box_id,
        destination_position: data.destination_position,
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, 'Failed to move grids'));
      }
    } catch (err) {
      let errorMessage = 'An error occurred while moving grid';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsMoving(false);
    }
  };

  return {
    moveGrid,
    isMoving,
    error,
    clearError,
  };
};
