import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL } from '@app/common/constants/api';
import { parseApiError } from '@app/common/utils/api/errorHandling';

/**
 * Configuration for useCreateResource hook
 * @template TInput - Input data type for creation
 * @template TOutput - Output response type from API
 */
export interface UseCreateResourceConfig<TInput, TOutput> {
  /** API endpoint for creation */
  endpoint: string;
  /** Error message to show if creation fails */
  errorMessage: string;
  /** Optional function to transform input data before sending to API */
  transformPayload?: (data: TInput) => Record<string, any>;
  /** Optional function to transform API response */
  transformResponse?: (response: any) => TOutput;
  /** Optional function to build URL dynamically (for parameterized endpoints) */
  buildUrl?: (endpoint: string, data: TInput) => string;
}

/**
 * Generic return type for create hooks
 */
export interface UseCreateResourceReturn<TInput, TOutput> {
  create: (data: TInput) => Promise<TOutput | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

/**
 * Generic hook for creating resources
 * Eliminates duplication across all create hooks
 * 
 * @example
 * const { create, isCreating, error, clearError } = useCreateResource({
 *   endpoint: POST_API.CREATE_PROJECT,
 *   errorMessage: 'Failed to create project',
 *   transformPayload: (data) => ({ ...data, extra: 'field' }),
 * });
 */
export function useCreateResource<TInput, TOutput>({
  endpoint,
  errorMessage,
  transformPayload,
  transformResponse,
  buildUrl,
}: UseCreateResourceConfig<TInput, TOutput>): UseCreateResourceReturn<TInput, TOutput> {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const create = async (data: TInput): Promise<TOutput | null> => {
    setIsCreating(true);
    setError(null);

    try {
      // Build URL (use custom builder if provided, otherwise use endpoint directly)
      const url = buildUrl 
        ? buildUrl(getRequestURL(DJANGO_URL, endpoint), data)
        : getRequestURL(DJANGO_URL, endpoint);

      // Transform payload if transformer provided, otherwise use data as-is
      const payload = transformPayload ? transformPayload(data) : data as Record<string, unknown>;

      // Make API request
      const response = await postResource(url, payload);

      if (response.ok) {
        const result = await response.json();
        // Transform response if transformer provided, otherwise return as-is
        return transformResponse ? transformResponse(result) : result;
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, errorMessage));
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : errorMessage;
      setError(errorMsg);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    create,
    isCreating,
    error,
    clearError,
  };
}