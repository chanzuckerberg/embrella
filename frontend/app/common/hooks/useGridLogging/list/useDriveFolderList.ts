import { API } from '@app/common/constants/api';
import { DocSpacesResponse, ExternalResource } from '@app/common/types/gridLogging/externalResource';
import { useListResource } from '../base/useListResource';

/**
 * Hook to fetch Google Drive folders from the external_links API.
 * Uses the /api/external-resources/doc_spaces/?system_name=Google%20Drive endpoint.
 */
export const useDriveFolderList = () => {
  const { items, isSuccess, totalCount } = useListResource({
    endpoint: `${API.EXTERNAL_RESOURCES_DOC_SPACES}?system_name=${encodeURIComponent('Google Drive')}`,
    selectItems: (data: DocSpacesResponse) => data.doc_spaces || [],
    getTotalCount: (data: DocSpacesResponse) => data.count || 0,
  });

  // Map ExternalResource to drive folder format for backwards compatibility
  const folders = (items as ExternalResource[]).map((resource) => ({
    id: resource.id,
    name: resource.name,
    url: resource.url,
    folder_id: resource.metadata?.folder_id as string | undefined,
  }));

  return {
    folders,
    isSuccess,
    totalCount,
  };
};
