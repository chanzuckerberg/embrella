/**
 * Shared filter configs for both Grids and Grid Boxes tabs.
 * Re-exports the grid filter configs since both tabs use the same filter categories.
 */
export { GRID_FILTER_CONFIGS as SHARED_FILTER_CONFIGS } from '@app/components/GridsView/constants/filters';
export type { GridFilterCategory, GridFilterConfig, GridFilterId } from '@app/components/GridsView/types';
