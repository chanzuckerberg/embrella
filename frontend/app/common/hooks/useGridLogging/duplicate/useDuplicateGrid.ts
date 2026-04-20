import { useState, useCallback } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { postResource } from '@app/common/queries/fetchResource';
import { DuplicateGridData, DuplicateGridResponse } from '@app/common/types/gridLogging/entities/grid';
import { parseApiError } from '@app/common/utils/api/errorHandling';

interface UseDuplicateGridResult {
  duplicateGrid: (data: DuplicateGridData) => Promise<DuplicateGridResponse | null>;
  isDuplicating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useDuplicateGrid = (): UseDuplicateGridResult => {
  const [isDuplicating, setIsDuplicating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const duplicateGrid = async (data: DuplicateGridData): Promise<DuplicateGridResponse | null> => {
    setIsDuplicating(true);
    setError(null);

    try {
      const url = getRequestURL(DJANGO_URL, POST_API.DUPLICATE_GRID).replace('grid_id', data.grid_id.toString());

      const response = await postResource(url, {
        destination_grid_box_id: data.destination_grid_box_id,
        number_to_copy: data.number_to_copy,
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, 'Failed to duplicate grid'));
      }
    } catch (err) {
      let errorMessage = 'An error occurred while duplicating grid';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsDuplicating(false);
    }
  };

  return {
    duplicateGrid,
    isDuplicating,
    error,
    clearError,
  };
};
