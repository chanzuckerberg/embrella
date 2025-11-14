import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { CreateFreezingSessionData, FreezingSessionCreateResponse } from '@app/common/types/gridLogging/freezingSessionList';


interface UseCreateFreezingSessionResult {
  createFreezingSession: (data: CreateFreezingSessionData) => Promise<FreezingSessionCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateFreezingSession = (): UseCreateFreezingSessionResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createFreezingSession = async (data: CreateFreezingSessionData): Promise<FreezingSessionCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_FREEZING_SESSION), {
        user: data.user,
        device: data.device,
        device_temperature: data.device_temperature,
        humidity: data.humidity,
        ...(data.notes_page && { notes_page: data.notes_page }),
      });

      if (response.ok) {
        const result = await response.json();
        return result.freezing_session || result;
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create freezing session');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createFreezingSession,
    isCreating,
    error,
    clearError,
  };
};