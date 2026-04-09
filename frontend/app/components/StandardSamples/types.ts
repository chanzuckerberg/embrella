import { GridBoxChildGrid } from '@app/components/GridInventory/GridBoxesView/types';

export interface StandardSampleData {
  specimen: {
    id: number;
    name: string;
  };
  availableGridCount: number;
  pointOfContact: string | null;
  grids: GridBoxChildGrid[];
}
