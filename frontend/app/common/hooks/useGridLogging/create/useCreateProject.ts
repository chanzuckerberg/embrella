import { POST_API } from '@app/common/constants/api';
import { CreateProjectData, ProjectCreateResponse } from '@app/common/types/gridLogging/entities/projectList';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateProject = () => {
  const { create, ...rest } = useCreateResource<CreateProjectData, ProjectCreateResponse>({
    endpoint: POST_API.CREATE_PROJECT,
    errorMessage: 'Failed to create project',
    transformPayload: (data) => ({
      name: data.name,
      description: data.description || '',
      project_leader: data.project_leader || null,
      confluence_space: data.confluence_space || null,
      google_drive_folder: data.google_drive_folder || null,
    }),
  });

  return {
    createProject: create,
    ...rest,
  };
};
