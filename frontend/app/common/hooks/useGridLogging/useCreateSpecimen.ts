import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { CreateSpecimenData, SpecimenCreateResponse } from '@app/common/types/gridLogging/specimenList';

interface UseCreateSpecimenResult {
  createSpecimen: (data: CreateSpecimenData) => Promise<SpecimenCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateSpecimen = (): UseCreateSpecimenResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createSpecimen = async (data: CreateSpecimenData): Promise<SpecimenCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const payload: Record<string, any> = {};
      
      if (data.notes) payload.notes = data.notes;
      if (data.notes_page !== undefined) payload.notes_page = data.notes_page;
      if (data.sample_ids && data.sample_ids.length > 0) payload.sample_ids = data.sample_ids;

      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_SPECIMEN), payload);

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        
        // Handle validation errors
        let errorMsg = 'Failed to create specimen';
        
        if (errorData.detail) {
          if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
            // Extract field-specific errors
            const fieldErrors = Object.entries(errorData.detail)
              .map(([field, messages]) => {
                const msgArray = Array.isArray(messages) ? messages : [messages];
                return `${field}: ${msgArray.join(', ')}`;
              })
              .join('; ');
            errorMsg = fieldErrors;
          } else if (typeof errorData.detail === 'string') {
            errorMsg = errorData.detail;
          }
        } else if (errorData.error) {
          errorMsg = errorData.error;
        }

        throw new Error(errorMsg);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred while creating specimen';
      setError(errorMessage);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createSpecimen,
    isCreating,
    error,
    clearError,
  };
};