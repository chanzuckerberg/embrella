import { POST_API } from '@app/common/constants/api';
import {
  CreateExternalResourceRequest,
  CreateExternalResourceResponse,
} from '@app/common/types/gridLogging/externalResource';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateExternalResource = () => {
  const { create, ...rest } = useCreateResource<CreateExternalResourceRequest, CreateExternalResourceResponse>({
    endpoint: POST_API.CREATE_EXTERNAL_RESOURCE,
    errorMessage: 'Failed to create external resource',
    transformPayload: (data) => ({
      resource_type: data.resource_type,
      system_name: data.system_name,
      name: data.name,
      url: data.url,
      ...(data.metadata && { metadata: data.metadata }),
    }),
    transformResponse: (result) => result as CreateExternalResourceResponse,
  });

  return {
    createExternalResource: create,
    ...rest,
  };
};
