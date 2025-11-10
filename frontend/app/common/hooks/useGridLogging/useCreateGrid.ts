import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';

export interface CreateGridData {
  grid_box: number;
  name: string;
  user: number;
  specimen: number;
  intended_project: number;
  position_in_box: number;
  freezing_session?: number;
  notes?: string;
  clipped?: boolean;
  blot_time?: number;
  blot_force?: number;
  blot_distance?: number;
  copy_number?: number;
}

export interface GridCreateResponse {
  id: number;
  name: string;
  user: number;
  specimen: number;
  intended_project: number;
  grid_box: number;
  position_in_box: number;
  freezing_session?: number;
  notes?: string;
  clipped: boolean;
  trashed: boolean;
  blot_time?: number;
  blot_force?: number;
  blot_distance?: number;
  copy_number: number;
}

interface UseCreateGridResult {
  createGrid: (data: CreateGridData) => Promise<GridCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateGrid = (): UseCreateGridResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createGrid = async (data: CreateGridData): Promise<GridCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_GRID), {
        name: data.name,
        user: data.user,
        specimen: data.specimen,
        intended_project: data.intended_project,
        grid_box: data.grid_box,
        position_in_box: data.position_in_box,
        ...(data.freezing_session && { freezing_session: data.freezing_session }),
        ...(data.notes && { notes: data.notes }),
        clipped: data.clipped || false,
        ...(data.blot_time && { blot_time: data.blot_time }),
        ...(data.blot_force && { blot_force: data.blot_force }),
        ...(data.blot_distance && { blot_distance: data.blot_distance }),
        copy_number: data.copy_number || 1,
      });

      console.log('Gridresponse', response);
      if (response.ok) {
        const result = await response.json();
        console.log('result', result);
        console.log('result.grid', result.grid);
        return result.grid || result;
      } else {
        const errorData = await response.json();
        console.log('errorData', errorData);

        // Handle validation errors with detailed messages
        let errorMsg = 'Failed to create grid';

        if (errorData.detail) {
          // If detail is an object with field-specific errors
          if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
            // Extract all field errors and combine them
            const fieldErrors = Object.entries(errorData.detail)
              .map(([_field, messages]) => {
                const msgArray = Array.isArray(messages) ? messages : [messages];
                return msgArray.join(', ');
              })
              .join('. ');
            errorMsg = fieldErrors;
          }
          // If detail is a string, use it directly
          else if (typeof errorData.detail === 'string') {
            errorMsg = errorData.detail;
          }
          // If detail is an array, join the messages
          else if (Array.isArray(errorData.detail)) {
            errorMsg = errorData.detail.join(', ');
          }
        } else {
          // Fallback to generic error message
          errorMsg = errorData.message || errorData.error || 'Failed to create grid';
        }

        const cleanError = errorMsg.replace(/^Error:\s*/i, '').trim();
        throw new Error(cleanError);
      }
    } catch (err) {
      let errorMessage = 'An error occurred while creating grid';
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
    createGrid,
    isCreating,
    error,
    clearError,
  };
};