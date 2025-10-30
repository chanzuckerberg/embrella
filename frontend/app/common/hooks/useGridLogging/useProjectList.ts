import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { ProjectsListResponse, transformProject } from '@app/common/types/gridLogging/projectList';
import { API } from '@app/common/constants/api';
import { useMemo } from 'react';

export const useProjectsList = () => {
  // Note: The API requires valid=true parameter
  const { data, isSuccess } = useFetchData<ProjectsListResponse>(API.PROJECTS_LIST, { valid: 'true' });

  const projects = useMemo(() => {
    if (!data) return [];
    return data.map(transformProject);
  }, [data]);

  return {
    projects,
    isSuccess,
    rawData: data,
  };
};
