import { useState, useEffect, useCallback } from 'react';
import { DJANGO_URL, API } from '../../constants/api';
import { GridDetailsResponse } from '../../types/gridLogging/gridDetails';

interface UseGridDetailsParams {
  puckId: number;
  positionInPuck: number;
  gridId: number;
}

interface UseGridDetailsReturn {
  gridDetails: GridDetailsResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useGridLoggingGridDetails = ({
  puckId,
  positionInPuck,
  gridId,
}: UseGridDetailsParams): UseGridDetailsReturn => {
  const [gridDetails, setGridDetails] = useState<GridDetailsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGridDetails = useCallback(async () => {
    if (!puckId || !positionInPuck || !gridId) {
      setError('Missing required parameters');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${DJANGO_URL}${API.GRID_LOGGING_GRID_DETAILS}`
        .replace('puck_id', puckId.toString())
        .replace('position_in_puck', positionInPuck.toString())
        .replace('grid_id', gridId.toString());

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data: GridDetailsResponse = await response.json();
      setGridDetails(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch grid details';
      setError(errorMessage);
      console.error('Error fetching grid details:', err);
    } finally {
      setLoading(false);
    }
  }, [puckId, positionInPuck, gridId]);

  useEffect(() => {
    fetchGridDetails();
  }, [fetchGridDetails]);

  return {
    gridDetails,
    loading,
    error,
    refetch: fetchGridDetails,
  };
};
