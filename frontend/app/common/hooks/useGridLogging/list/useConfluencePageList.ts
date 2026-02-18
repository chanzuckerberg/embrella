import { API } from '@app/common/constants/api';
import { DocPagesResponse, ExternalResource } from '@app/common/types/gridLogging/externalResource';
import { useListResource } from '../base/useListResource';

/**
 * Hook to fetch Confluence pages from the external_links API.
 * Uses the /api/external-resources/doc_pages/?system_name=Confluence endpoint.
 */
export const useConfluencePageList = () => {
  const { items, isSuccess, totalCount, refetch } = useListResource({
    endpoint: `${API.EXTERNAL_RESOURCES_DOC_PAGES}?system_name=Confluence`,
    selectItems: (data: DocPagesResponse) => data.doc_pages || [],
    getTotalCount: (data: DocPagesResponse) => data.count || 0,
  });

  // Map ExternalResource to confluence page format for backwards compatibility
  const pages = (items as ExternalResource[]).map((resource) => ({
    id: resource.id,
    name: resource.name,
    url: resource.url,
    page_id: resource.metadata?.page_id as string | undefined,
  }));

  return {
    pages,
    isSuccess,
    totalCount,
    refetch,
  };
};
