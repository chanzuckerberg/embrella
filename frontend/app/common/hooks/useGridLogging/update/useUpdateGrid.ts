import { useState, useCallback } from 'react';
import { patchResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { parseApiError } from '@app/common/utils/api/errorHandling';

interface UpdateGridData {
  grid_id: number;
  name?: string;
  copy_number?: number;
  notes?: string;
  freezing_session?: number;
  specimen?: number;
  intended_project?: number;
  position_in_box?: number;
  blot_time?: number;
  blot_force?: number;
  blot_distance?: number;
}

interface UpdateGridResponse {
  success: boolean;
  message: string;
  grid: {
    id: number;
    name: string;
    notes: string;
    blot_time: number;
    blot_force: number;
    blot_distance: number;
    user: string | null;
    position_in_box: number;
    copy_number: number;
  };
}

interface UseUpdateGridResult {
  updateGrid: (data: UpdateGridData) => Promise<UpdateGridResponse | null>;
  isUpdating: boolean;
  error: string | null;
  clearError: () => void;
}

export const useUpdateGrid = (): UseUpdateGridResult => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const updateGrid = async (data: UpdateGridData): Promise<UpdateGridResponse | null> => {
    setIsUpdating(true);
    setError(null);

    try {
      // Build the URL by replacing grid_id placeholder
      const url = getRequestURL(DJANGO_URL, POST_API.UPDATE_GRID).replace('grid_id', data.grid_id.toString());

      const payload: Record<string, unknown> = {};
      if (data.name !== undefined) payload.name = data.name;
      if (data.copy_number !== undefined) payload.copy_number = data.copy_number;
      if (data.notes !== undefined) payload.notes = data.notes;
      if (data.freezing_session !== undefined) payload.freezing_session = data.freezing_session;
      if (data.specimen !== undefined) payload.specimen = data.specimen;
      if (data.intended_project !== undefined) payload.intended_project = data.intended_project;
      if (data.position_in_box !== undefined) payload.position_in_box = data.position_in_box;
      if (data.blot_time !== undefined) payload.blot_time = data.blot_time;
      if (data.blot_force !== undefined) payload.blot_force = data.blot_force;
      if (data.blot_distance !== undefined) payload.blot_distance = data.blot_distance;

      const response = await patchResource(url, payload);

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(parseApiError(errorData, 'Failed to update grid'));
      }
    } catch (err) {
      let errorMessage = 'An error occurred while updating grid';
      if (err instanceof Error) {
        errorMessage = err.message.replace(/^Error:\s*/i, '').trim();
      }
      setError(errorMessage);
      return null;
    } finally {
      setIsUpdating(false);
    }
  };

  return {
    updateGrid,
    isUpdating,
    error,
    clearError,
  };
};
