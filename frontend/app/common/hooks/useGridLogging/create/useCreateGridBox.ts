import { POST_API } from '@app/common/constants/api';
import { GridBoxCreateResponse } from '@app/common/types/gridLogging/gridBox';
import { useCreateResource } from '../base/useCreateResource';

interface CreateGridBoxData {
  puck_id: number;
  puckName?: string;
  gridBoxName: string;
  color: string;
  numbering: string;
  position_in_puck: number;
  max_grids: number;
}

export const useCreateGridBox = () => {
  const { create, ...rest } = useCreateResource<CreateGridBoxData, GridBoxCreateResponse>({
    endpoint: POST_API.CREATE_GRID_BOX,
    errorMessage: 'Failed to create grid box',
    buildUrl: (endpoint, data) => endpoint.replace('puck_id', data.puck_id.toString()),
    transformPayload: (data) => ({
      name: data.gridBoxName,
      color: data.color,
      numbering: data.numbering,
      position_in_puck: data.position_in_puck,
      max_grids: data.max_grids,
      puck_name: data.puckName,
    }),
    transformResponse: (result) => result.grid_box,
  });

  return {
    createGridBox: create,
    ...rest,
  };
};