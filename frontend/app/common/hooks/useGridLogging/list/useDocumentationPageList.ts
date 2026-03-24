import { API } from '@app/common/constants/api';
import { DocPagesResponse, ExternalResource } from '@app/common/types/gridLogging/externalResource';
import { useListResource } from '../base/useListResource';

/**
 * All documentation pages (Confluence, Google Docs/Drive, Benchling, etc.)
 * — no system_name filter.
 */
export const useDocumentationPageList = () => {
  const { items, isSuccess, totalCount, refetch } = useListResource({
    endpoint: API.EXTERNAL_RESOURCES_DOC_PAGES,
    selectItems: (data: DocPagesResponse) => data.doc_pages || [],
    getTotalCount: (data: DocPagesResponse) => data.count || 0,
  });

  const pages = (items as ExternalResource[]).map((resource) => ({
    id: resource.id,
    name: resource.name,
    url: resource.url,
    system_name: resource.system_name,
    page_id: resource.metadata?.page_id as string | undefined,
  }));

  return {
    pages,
    isSuccess,
    totalCount,
    refetch,
  };
};
