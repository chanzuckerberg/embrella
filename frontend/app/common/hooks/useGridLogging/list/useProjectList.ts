import { API } from '@app/common/constants/api';
import { ProjectListResponse, transformProject } from '@app/common/types/gridLogging/projectList';
import { useListResource } from '../base/useListResource';

export const useProjectsList = () => {
  const { transformedItems, isSuccess, rawData, refetch } = useListResource({
    endpoint: API.PROJECTS_LIST,
    selectItems: (data: ProjectListResponse) => Array.isArray(data) ? data : [],
    getTotalCount: (data: ProjectListResponse) => Array.isArray(data) ? data.length : 0,
    transform: transformProject,
    searchParams: { valid: 'true' },
  });

  return {
    projects: transformedItems,
    isSuccess,
    rawData,
    refetch,
  };
};