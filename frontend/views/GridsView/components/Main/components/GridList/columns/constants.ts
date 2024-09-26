import { AccessorFnColumnDef } from "@tanstack/react-table";
import { GridData } from "@/common/types";
import {
  GRID_COLUMN,
  GridColumnDef,
} from "@/views/GridsView/components/Main/components/GridList/columns/types";
import {
  getCryogridAccessorFn,
  getFreezingPlanAccessorFn,
  getFreezingSessionAccessorFn,
  getMSIAccessorFn,
  getProjectAccessorFn,
  getUpdatedAtAccessorFn,
} from "@/views/GridsView/components/Main/components/GridList/columns/accessor";

export const GRID_COLUMN_ACCESSOR_FN: Record<
  keyof typeof GRID_COLUMN,
  AccessorFnColumnDef<GridData>["accessorFn"]
> = {
  CRYOGRID: getCryogridAccessorFn,
  FREEZING_PLAN: getFreezingPlanAccessorFn,
  FREEZING_SESSION: getFreezingSessionAccessorFn,
  MSI: getMSIAccessorFn,
  PROJECT: getProjectAccessorFn,
  UPDATED_AT: getUpdatedAtAccessorFn,
};

export const GRID_COLUMN_ID: Record<
  keyof typeof GRID_COLUMN,
  GridColumnDef["id"]
> = {
  CRYOGRID: "cryogrid",
  FREEZING_PLAN: "freezingPlan",
  FREEZING_SESSION: "freezingSession",
  MSI: "msi",
  PROJECT: "project",
  UPDATED_AT: "updatedAt",
};
