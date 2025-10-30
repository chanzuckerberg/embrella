import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { GridBoxCreateResponse } from '@app/common/types/gridLogging/gridBox';

interface CreateGridBoxData {
  puck_id: number;
  puckName?: string;
  gridBoxName: string;
  color: string;
  numbering: string;
  position_in_puck: number;
  max_grids: number;
}

interface UseCreateGridBoxResult {
  createGridBox: (data: CreateGridBoxData) => Promise<GridBoxCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateGridBox = (): UseCreateGridBoxResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createGridBox = async (data: CreateGridBoxData): Promise<GridBoxCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      // Build the URL by replacing puck_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.CREATE_GRID_BOX).replace('puck_id', data.puck_id.toString());

      const response = await postResource(url, {
        name: data.gridBoxName,
        color: data.color,
        numbering: data.numbering,
        position_in_puck: data.position_in_puck,
        max_grids: data.max_grids,
        puck_name: data.puckName,
      });

      if (response.ok) {
        const result = await response.json();
        return result.grid_box;
      } else {
        const errorData = await response.json();
        const errorMsg = errorData.detail || errorData.error || 'Failed to create grid box';

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
      let errorMessage = 'An error occurred while creating grid box';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createGridBox,
    isCreating,
    error,
    clearError,
  };
};
