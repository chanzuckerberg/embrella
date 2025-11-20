import { POST_API } from '@app/common/constants/api';
import {
  CreateFreezingSessionData,
  FreezingSessionCreateResponse,
} from '@app/common/types/gridLogging/entities/freezingSessionList';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateFreezingSession = () => {
  const { create, ...rest } = useCreateResource<CreateFreezingSessionData, FreezingSessionCreateResponse>({
    endpoint: POST_API.CREATE_FREEZING_SESSION,
    errorMessage: 'Failed to create freezing session',
    transformPayload: (data) => ({
      user: data.user,
      device: data.device,
      device_temperature: data.device_temperature,
      humidity: data.humidity,
      ...(data.notes_page && { notes_page: data.notes_page }),
    }),
    transformResponse: (result) => {
      const response = result as { freezing_session?: FreezingSessionCreateResponse };
      return response.freezing_session || (result as FreezingSessionCreateResponse);
    },
  });

  return {
    createFreezingSession: create,
    ...rest,
  };
};
