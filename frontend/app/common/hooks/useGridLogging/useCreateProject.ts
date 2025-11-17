import { useState, useCallback } from 'react';
import { postResource } from '@app/common/queries/fetchResource';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { getRequestURL } from '@app/common/queries/utils';
import { CreateProjectData, ProjectCreateResponse } from '@app/common/types/gridLogging/projectList';

interface UseCreateProjectResult {
  createProject: (data: CreateProjectData) => Promise<ProjectCreateResponse | null>;
  isCreating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useCreateProject = (): UseCreateProjectResult => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createProject = async (data: CreateProjectData): Promise<ProjectCreateResponse | null> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_PROJECT), {
        name: data.name,
        description: data.description || '',
        project_leader: data.project_leader || null,
        confluence_space: data.confluence_space || null,
        google_drive_folder: data.google_drive_folder || null,
      });

      if (response.ok) {
        const result = await response.json();
        return result;
      } else {
        const errorData = await response.json();
        
        // Handle validation errors
        let errorMsg = 'Failed to create project';
        
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
      const errorMessage = err instanceof Error ? err.message : 'An error occurred while creating project';
      setError(errorMessage);
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createProject,
    isCreating,
    error,
    clearError,
  };
};