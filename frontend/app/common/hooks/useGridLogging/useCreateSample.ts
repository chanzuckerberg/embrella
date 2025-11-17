import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { CreateSampleData, SampleCreateResponse } from '@app/common/types/gridLogging/specimenList';

interface UseCreateSampleResult {
  createSample: (data: CreateSampleData) => Promise<SampleCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateSample = (): UseCreateSampleResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createSample = async (data: CreateSampleData): Promise<SampleCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_SAMPLE), {
        name: data.name,
        ontology: data.ontology || '',
      });

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        
        // Handle validation errors
        let errorMsg = 'Failed to create sample';
        
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
      const errorMessage = err instanceof Error ? err.message : 'An error occurred while creating sample';
      setError(errorMessage);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createSample,
    isCreating,
    error,
    clearError,
  };
};