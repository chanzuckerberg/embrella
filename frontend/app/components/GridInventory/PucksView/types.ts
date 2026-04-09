import { GridBoxData } from '@app/components/GridInventory/GridBoxesView/types';

export interface PuckData {
  puck: { id: number; name: string };
  color: string;
  colorDisplay: string;
  caneName: string | null;
  positionInCane: number | null;
  maxBoxes: number;
  gridBoxCount: number;
  userName: string | null;
  gridBoxes: GridBoxData[];
}
