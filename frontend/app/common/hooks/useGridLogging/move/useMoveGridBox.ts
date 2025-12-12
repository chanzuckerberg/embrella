import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { patchResource } from '@app/common/queries/fetchResource';
import { MoveGridBoxData, MoveGridBoxResponse } from '@app/common/types/gridLogging/entities/gridBox';
import { parseApiError } from '@app/common/utils/api/errorHandling';

interface UseMoveGridBoxResult {
  moveGridBox: (data: MoveGridBoxData) => Promise<MoveGridBoxResponse | null>;
  isMoving: boolean;
  error: string | null;
  clearError: () => void;
}

export const useMoveGridBox = (): UseMoveGridBoxResult => {
  const [isMoving, setIsMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const moveGridBox = async (data: MoveGridBoxData): Promise<MoveGridBoxResponse | null> => {
    setIsMoving(true);
    setError(null);

    try {
      // Build the URL by replacing grid_box_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.MOVE_GRID_BOX).replace('grid_box_id', data.grid_box_id.toString());

      const response = await patchResource(url, {
        destination_puck_id: data.destination_puck_id,
        destination_position: data.destination_position,
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, 'Failed to move grid boxes'));
      }
    } catch (err) {
      let errorMessage = 'An error occurred while moving grid box';
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
    moveGridBox,
    isMoving,
    error,
    clearError,
  };
};
