import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { patchResource } from '@app/common/queries/fetchResource';


export interface MoveGridBoxData {
  grid_box_id: number;
  destination_puck_id: number;
  destination_position: number;
}

export interface MoveGridBoxResponse {
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
    puck: number;
  };
}

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
      const url = getRequestURL(DJANGO_URL, POST_API.MOVE_GRID_BOX).replace(
        'grid_box_id',
        data.grid_box_id.toString()
      );

      const response = await patchResource(url, {
        destination_puck_id: data.destination_puck_id,
        destination_position: data.destination_position,
      });

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        const errorMsg = errorData.error || errorData.detail || 'Failed to move grid box';

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