import { useState } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { PucksList, CreatePuckData } from '@app/common/types/gridLogging/puckList';

interface UseCreatePuckResult {
  createPuck: (data: CreatePuckData) => Promise<PucksList | null>;
  isCreating: boolean;
  error: string | null;
}

export const useCreatePuck = (): UseCreatePuckResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        const errorMsg = errorData.message || errorData.error || 'Failed to create puck';
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
  };
};
