import { API } from '@app/common/constants/api';
import { ProjectListResponse, transformProject } from '@app/common/types/gridLogging/entities/projectList';
import { useListResource } from '../base/useListResource';

export const useProjectsList = () => {
  const { transformedItems, isSuccess, rawData, refetch } = useListResource({
    endpoint: API.PROJECTS,
    selectItems: (data: ProjectListResponse) => (Array.isArray(data) ? data : []),
    getTotalCount: (data: ProjectListResponse) => (Array.isArray(data) ? data.length : 0),
    transform: transformProject,
  });

  return {
    projects: transformedItems,
    isSuccess,
    rawData,
    refetch,
  };
};
