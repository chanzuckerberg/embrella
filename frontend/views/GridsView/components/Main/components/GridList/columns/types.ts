import { CellContext, ColumnDef } from "@tanstack/react-table";
import { GridData } from "@/app/common/types/types";
import { LinkTValue } from "@/app/common/components/Table/components/CellComponent/types";

export enum GRID_COLUMN {
  CRYOGRID = "CRYOGRID",
  FREEZING_PLAN = "FREEZING_PLAN",
  FREEZING_SESSION = "FREEZING_SESSION",
  MSI = "MSI",
  PROJECT = "PROJECT",
  UPDATED_AT = "UPDATED_AT",
}

export type GridAccessorReturnType = string | LinkTValue | LinkTValue[];

export type GridColumnDef = ColumnDef<GridData, GridAccessorReturnType>;

export type GridColumnDefCellContext<TData> = CellContext<GridData, TData>;
