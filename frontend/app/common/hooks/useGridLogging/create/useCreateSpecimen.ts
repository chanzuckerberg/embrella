import { POST_API } from '@app/common/constants/api';
import { CreateSpecimenData, SpecimenCreateResponse } from '@app/common/types/gridLogging/specimenList';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateSpecimen = () => {
  const { create, ...rest } = useCreateResource<CreateSpecimenData, SpecimenCreateResponse>({
    endpoint: POST_API.CREATE_SPECIMEN,
    errorMessage: 'Failed to create specimen',
    transformPayload: (data) => {
      const payload: Record<string, any> = {};
      if (data.notes) payload.notes = data.notes;
      if (data.notes_page !== undefined) payload.notes_page = data.notes_page;
      if (data.sample_ids && data.sample_ids.length > 0) payload.sample_ids = data.sample_ids;
      return payload;
    },
  });

  return {
    createSpecimen: create,
    ...rest,
  };
};