import { POST_API } from '@app/common/constants/api';
import { CreateSampleData, SampleCreateResponse } from '@app/common/types/gridLogging/specimenList';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateSample = () => {
  const { create, ...rest } = useCreateResource<CreateSampleData, SampleCreateResponse>({
    endpoint: POST_API.CREATE_SAMPLE,
    errorMessage: 'Failed to create sample',
    transformPayload: (data) => ({
      name: data.name,
      ontology: data.ontology || '',
    }),
  });

  return {
    createSample: create,
    ...rest,
  };
};