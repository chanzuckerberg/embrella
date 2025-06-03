import { useState, useEffect, useCallback, useRef } from 'react';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { API, DJANGO_URL } from '@app/common/constants/api';

// Define cache key type
type CacheKey = string;

// Define cache item type with expiration
interface CacheItem {
  data: MetadataVizResponse;
  timestamp: number;
}

// Cache expiration time in milliseconds (5 minutes)
const CACHE_EXPIRATION = 5 * 60 * 1000;

// Debounce delay in milliseconds
const DEBOUNCE_DELAY = 300;

export const useSortedData = (
  data?: MetadataVizResponse,
  onSortChange?: (sortBy: string, sortDirection: 'asc' | 'desc') => void
) => {
  const [sortEnabled, setSortEnabled] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('Select Metric');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [sortedData, setSortedData] = useState<MetadataVizResponse | undefined>(data);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Refs for caching and debouncing
  const cacheRef = useRef<Map<CacheKey, CacheItem>>(new Map());
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Keep track of the latest data prop
  const dataRef = useRef(data);
  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  // Update sortedData when data prop changes (but not during sorting operations)
  useEffect(() => {
    if (!isLoading) {
      setSortedData(data);
    }
  }, [data, isLoading]);

  /**
   * Generate a cache key based on session, run number, filters, and sort parameters
   */
  const generateCacheKey = useCallback(
    (
      sessionName: string,
      runNumber: string,
      filters: any,
      sortByValue: string,
      sortDirectionValue: 'asc' | 'desc'
    ): CacheKey => {
      return `${sessionName}_${runNumber}_${JSON.stringify(filters)}_${sortByValue}_${sortDirectionValue}`;
    },
    []
  );

  /**
   * Apply client-side sorting to data for immediate feedback
   */
  const applySortClientSide = useCallback(
    (sourceData: MetadataVizResponse, sortByValue: string, sortDirectionValue: 'asc' | 'desc') => {
      if (!sourceData || !sortEnabled || !sortByValue || sortByValue === 'Select Metric') {
        return sourceData;
      }

      const clientSortedData = { ...sourceData };

      if (clientSortedData.accepted_results) {
        // Create a new array to avoid mutating the original
        clientSortedData.accepted_results = [...clientSortedData.accepted_results].sort((a, b) => {
          // Handle position name sorting separately
          if (sortByValue === 'position_name') {
            const aValue = a.name || '';
            const bValue = b.name || '';
            const comparison = aValue.localeCompare(bValue);
            return sortDirectionValue === 'asc' ? comparison : -comparison;
          }

          // Handle metric sorting
          const aValue = Number(a.metrics?.[sortByValue as keyof typeof a.metrics] ?? 0);
          const bValue = Number(b.metrics?.[sortByValue as keyof typeof b.metrics] ?? 0);
          return sortDirectionValue === 'asc' ? aValue - bValue : bValue - aValue;
        });
      }

      return clientSortedData;
    },
    [sortEnabled]
  );

  /**
   * Fetch sorted data from API with caching and debouncing
   */
  const fetchSortedData = useCallback(async () => {
    // Clear any existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    // Get the latest data from ref
    const currentData = dataRef.current;

    // Only fetch if sorting is enabled and a valid metric is selected
    if (!sortEnabled || !sortBy || sortBy === 'Select Metric' || !currentData) {
      setSortedData(currentData);
      return;
    }

    // Apply client-side sorting immediately for responsive UI
    const clientSortedData = applySortClientSide(currentData, sortBy, sortDirection);
    setSortedData(clientSortedData);

    // Create a cache key for this request
    const cacheKey = generateCacheKey(
      currentData.session_name,
      currentData.run_number,
      currentData.filters_applied,
      sortBy,
      sortDirection
    );

    // Check if we have a valid cached response
    const cachedItem = cacheRef.current.get(cacheKey);
    const now = Date.now();

    if (cachedItem && now - cachedItem.timestamp < CACHE_EXPIRATION) {
      // Use cached data if it's still valid
      setSortedData(cachedItem.data);
      return;
    }

    // Debounce the API call to prevent excessive requests
    debounceTimerRef.current = setTimeout(async () => {
      try {
        setIsLoading(true);

        // Build the API URL with sorting parameters
        let url = `${DJANGO_URL}${API.METADATA_VIZ}?session_name=${currentData.session_name}&run_number=${currentData.run_number}`;

        // Add filters if present
        if (currentData.filters_applied && currentData.filters_applied.filters) {
          const filterConfig = {
            filter_type: currentData.filters_applied.filter_type,
            filters: currentData.filters_applied.filters,
          };
          url += `&q=${encodeURIComponent(JSON.stringify(filterConfig))}`;
        }

        // Add sorting parameters
        url += `&sort_by=${encodeURIComponent(sortBy)}&sort_direction=${encodeURIComponent(sortDirection)}`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error('Failed to fetch sorted data');
        }

        const jsonData = await response.json();

        // Cache the response
        cacheRef.current.set(cacheKey, {
          data: jsonData,
          timestamp: Date.now(),
        });

        setSortedData(jsonData);

        // Still call onSortChange if provided (for backward compatibility)
        if (onSortChange) {
          onSortChange(sortBy, sortDirection);
        }
      } catch (error) {
        console.error('Error fetching sorted data:', error);
        // We already applied client-side sorting above, so no need to do it again here
      } finally {
        setIsLoading(false);
        debounceTimerRef.current = null;
      }
    }, DEBOUNCE_DELAY);
  }, [sortEnabled, sortBy, sortDirection, onSortChange, applySortClientSide, generateCacheKey]);

  // Fetch sorted data when sorting parameters change
  useEffect(() => {
    fetchSortedData();
  }, [fetchSortedData]);

  // Clean up debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return {
    sortEnabled,
    setSortEnabled,
    sortBy,
    setSortBy,
    sortDirection,
    setSortDirection,
    sortedData,
    isLoading,
  };
};
