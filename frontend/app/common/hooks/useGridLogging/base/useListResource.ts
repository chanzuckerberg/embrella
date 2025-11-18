import { useMemo } from 'react';
import { useFetchData } from '@hooks/useFetchData/useFetchData';

/**
 * Configuration for useListResource hook
 * @template TEntity - The entity type (e.g., Sample, Specimen)
 * @template TResponse - The API response type
 * @template TTransformed - The transformed entity type (optional)
 */
export interface UseListResourceConfig<TEntity, TResponse, TTransformed = TEntity> {
  /** API endpoint to fetch from */
  endpoint: string;
  /** Function to extract items array from response */
  selectItems: (response: TResponse) => TEntity[];
  /** Function to get total count from response */
  getTotalCount: (response: TResponse) => number;
  /** Optional transform function for each item */
  transform?: (item: TEntity) => TTransformed;
  /** Optional search params */
  searchParams?: Record<string, any>;
}

/**
 * Generic return type for list hooks
 */
export interface UseListResourceReturn<TEntity, TResponse, TTransformed = TEntity> {
  items: TEntity[];
  isSuccess: boolean;
  totalCount: number;
  transformedItems: TTransformed[];
  rawData?: TResponse;
  refetch?: () => void;
}

/**
 * Generic hook for fetching and transforming list data
 * Eliminates duplication across all list hooks
 */
export function useListResource<TEntity, TResponse, TTransformed = TEntity>({
  endpoint,
  selectItems,
  getTotalCount,
  transform,
  searchParams,
}: UseListResourceConfig<TEntity, TResponse, TTransformed>): UseListResourceReturn<
  TEntity,
  TResponse,
  TTransformed
> {
  const { data, isSuccess, refetch } = useFetchData<TResponse>(endpoint, searchParams);

  const items = useMemo(() => {
    if (!data) return [];
    return selectItems(data);
  }, [data, selectItems]);

  const transformedItems = useMemo(() => {
    if (!transform) return items as unknown as TTransformed[];
    return items.map(transform);
  }, [items, transform]);

  return {
    items,
    isSuccess,
    totalCount: data ? getTotalCount(data) : 0,
    transformedItems,
    rawData: data,
    refetch,
  };
}