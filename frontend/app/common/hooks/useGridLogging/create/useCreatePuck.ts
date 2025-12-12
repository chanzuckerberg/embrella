import { POST_API } from '@app/common/constants/api';
import { PuckList, CreatePuckData } from '@app/common/types/gridLogging/entities/puckList';
import { useCreateResource } from '../base/useCreateResource';

export const useCreatePuck = () => {
  const { create, ...rest } = useCreateResource<CreatePuckData, PuckList>({
    endpoint: POST_API.CREATE_PUCK,
    errorMessage: 'Failed to create puck',
    transformPayload: (data) => ({
      user: data.user_id,
      name: data.puckName,
      color: data.color,
      cane: data.cane,
      position_in_cane: data.position_in_cane,
    }),
  });

  return {
    createPuck: create,
    ...rest,
  };
};
