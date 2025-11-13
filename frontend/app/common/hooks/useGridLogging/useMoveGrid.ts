import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { patchResource } from '@app/common/queries/fetchResource';

export interface MoveGridData {
  grid_id: number;
  destination_grid_box_id: number;
  destination_position: number;
}

export interface MoveGridResponse {
  success: boolean;
  message: string;
  grid: {
    id: number;
    name: string;
    grid_box: number;
    position_in_box: number;
    user: number;
    specimen: number;
    freezing_session: number;
    clipped: boolean;
    trashed: boolean;
  };
}

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
      const url = getRequestURL(DJANGO_URL, POST_API.MOVE_GRID).replace(
        'grid_id',
        data.grid_id.toString()
      );

      const response = await patchResource(url, {
        destination_grid_box_id: data.destination_grid_box_id,
        destination_position: data.destination_position,
      });

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        const errorMsg = errorData.error || errorData.detail || 'Failed to move grid';

        // Extract user-friendly error message
        let cleanError = errorMsg;
        if (typeof errorMsg === 'object') {
          // Handle validation errors
          const errors = Object.entries(errorMsg).map(([key, value]) => {
            if (Array.isArray(value)) {
              return `${key}: ${value.join(', ')}`;
            }
            return `${key}: ${value}`;
          });
          cleanError = errors.join('; ');
        } else if (typeof errorMsg === 'string') {
          cleanError = errorMsg.replace(/^Error:\s*/i, '').trim();
        }

        throw new Error(cleanError);
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