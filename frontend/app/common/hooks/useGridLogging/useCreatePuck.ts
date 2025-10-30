import { useState } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { PucksList, CreatePuckData } from '@app/common/types/gridLogging/puckList';

interface UseCreatePuckResult {
  createPuck: (data: CreatePuckData) => Promise<PucksList | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreatePuck = (): UseCreatePuckResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => {
    setError(null);
  };

  const createPuck = async (data: CreatePuckData): Promise<PucksList | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_PUCK), {
        user: data.user_id,
        name: data.puckName,
        color: data.color,
        cane: data.cane,
        position_in_cane: data.position_in_cane,
      });

      if (response.ok) {
        const newPuck = await response.json();
        return newPuck;
      } else {
        const errorData = await response.json();

        // Handle validation errors with detailed messages
        let errorMsg = 'Failed to create puck';

        if (errorData.detail) {
          // If detail is an object with field-specific errors
          if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
            // Extract all field errors and combine them
            const fieldErrors = Object.entries(errorData.detail)
              .map(([field, messages]) => {
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
          errorMsg = errorData.message || errorData.error || 'Failed to create puck';
        }

        const cleanError = errorMsg.replace(/^Error:\s*/i, '').trim();
        throw new Error(cleanError);
      }
    } catch (err) {
      let errorMessage = 'An error occurred while creating puck';
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
    createPuck,
    isCreating,
    error,
    clearError,
  };
};
