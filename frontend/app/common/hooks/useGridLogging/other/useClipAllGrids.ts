import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';

export interface ClipAllGridsResponse {
  success: boolean;
  message: string;
  updated_count: number;
  grid_box_id: number;
  grid_box_name: string;
}

interface UseClipAllGridsResult {
  clipAllGrids: (gridBoxId: number) => Promise<ClipAllGridsResponse | null>;
  isClipping: boolean;
  error: string | null;
  clearError: () => void;
}

export const useClipAllGrids = (): UseClipAllGridsResult => {
  const [isClipping, setIsClipping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clipAllGrids = async (gridBoxId: number): Promise<ClipAllGridsResponse | null> => {
    setIsClipping(true);
    setError(null);

    try {
      // Build the URL by replacing grid_box_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.CLIP_ALL_GRIDS).replace('grid_box_id', gridBoxId.toString());

      const response = await postResource(url, {});

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        
        // Handle error responses
        let errorMsg = 'Failed to clip all grids';
        
        if (errorData.error) {
          errorMsg = errorData.error;
        } else if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        }

        const cleanError = errorMsg.replace(/^Error:\s*/i, '').trim();
        throw new Error(cleanError);
      }
    } catch (err) {
      let errorMessage = 'An error occurred while clipping all grids';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsClipping(false);
    }
  };

  return {
    clipAllGrids,
    isClipping,
    error,
    clearError,
  };
};