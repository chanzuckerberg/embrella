import { API } from '@app/common/constants/api';
import { DocSpacesResponse, ExternalResource } from '@app/common/types/gridLogging/externalResource';
import { useListResource } from '../base/useListResource';

/**
 * Hook to fetch Confluence spaces from the external_links API.
 * Uses the /api/external-resources/doc_spaces/?system_name=Confluence endpoint.
 */
export const useConfluenceSpaceList = () => {
  const { items, isSuccess, totalCount } = useListResource({
    endpoint: `${API.EXTERNAL_RESOURCES_DOC_SPACES}?system_name=Confluence`,
    selectItems: (data: DocSpacesResponse) => data.doc_spaces || [],
    getTotalCount: (data: DocSpacesResponse) => data.count || 0,
  });

  // Map ExternalResource to confluence space format for backwards compatibility
  const spaces = (items as ExternalResource[]).map((resource) => ({
    id: resource.id,
    name: resource.name,
    url: resource.url,
    space_id: resource.metadata?.space_id as string | undefined,
  }));

  return {
    spaces,
    isSuccess,
    totalCount,
  };
};
