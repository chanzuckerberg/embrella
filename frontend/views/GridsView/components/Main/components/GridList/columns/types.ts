import { CellContext, ColumnDef } from "@tanstack/react-table";
import { GridData } from "@/common/types";

export enum GRID_COLUMN {
  CRYOGRID = "CRYOGRID",
  FREEZING_PLAN = "FREEZING_PLAN",
  FREEZING_SESSION = "FREEZING_SESSION",
  MSI = "MSI",
  PROJECT = "PROJECT",
  UPDATED_AT = "UPDATED_AT",
}

export type GridColumnDef = ColumnDef<GridData>;

export type GridColumnDefCellContext<TData> = CellContext<GridData, TData>;
