import { useQuery } from '@tanstack/react-query';
import { DJANGO_URL, API } from '@app/common/constants/api';
import type { DocSpacesResponse, DocPagesResponse } from '@app/common/types/gridLogging';

/**
 * Fetch all documentation spaces (Confluence, Google Drive, Benchling, etc.)
 */
export const useDocumentationSpaces = () => {
  return useQuery({
    queryKey: ['documentation-spaces'],
    queryFn: async (): Promise<DocSpacesResponse> => {
      const response = await fetch(`${DJANGO_URL}${API.EXTERNAL_RESOURCES_DOC_SPACES}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch documentation spaces');
      }

      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch all documentation pages (Confluence pages, Benchling entries, etc.)
 */
export const useDocumentationPages = () => {
  return useQuery({
    queryKey: ['documentation-pages'],
    queryFn: async (): Promise<DocPagesResponse> => {
      const response = await fetch(`${DJANGO_URL}${API.EXTERNAL_RESOURCES_DOC_PAGES}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch documentation pages');
      }

      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch documentation spaces filtered by system name
 */
export const useDocumentationSpacesBySystem = (systemName?: string) => {
  return useQuery({
    queryKey: ['documentation-spaces', systemName],
    queryFn: async (): Promise<DocSpacesResponse> => {
      const url = systemName
        ? `${DJANGO_URL}${API.EXTERNAL_RESOURCES_DOC_SPACES}?system_name=${encodeURIComponent(systemName)}`
        : `${DJANGO_URL}${API.EXTERNAL_RESOURCES_DOC_SPACES}`;

      const response = await fetch(url, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch documentation spaces');
      }

      return response.json();
    },
    enabled: !!systemName || systemName === undefined,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
