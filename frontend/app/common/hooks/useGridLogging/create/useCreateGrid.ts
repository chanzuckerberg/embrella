import { POST_API } from '@app/common/constants/api';
import { CreateGridData, GridCreateResponse } from '@app/common/types/gridLogging/entities/grid';
import { useCreateResource } from '../base/useCreateResource';

export const useCreateGrid = () => {
  const { create, ...rest } = useCreateResource<CreateGridData, GridCreateResponse>({
    endpoint: POST_API.CREATE_GRID,
    errorMessage: 'Failed to create grid',
    transformPayload: (data) => ({
      name: data.name,
      user: data.user,
      specimen: data.specimen,
      intended_project: data.intended_project,
      grid_box: data.grid_box,
      position_in_box: data.position_in_box,
      ...(data.freezing_session && { freezing_session: data.freezing_session }),
      ...(data.notes && { notes: data.notes }),
      clipped: data.clipped || false,
      ...(data.blot_time && { blot_time: data.blot_time }),
      ...(data.blot_force && { blot_force: data.blot_force }),
      ...(data.blot_distance && { blot_distance: data.blot_distance }),
      copy_number: data.copy_number || 1,
    }),
    transformResponse: (result) => result.grid || result,
  });

  return {
    createGrid: create,
    ...rest,
  };
};