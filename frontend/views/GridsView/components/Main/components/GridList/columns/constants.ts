import { AccessorFnColumnDef } from "@tanstack/react-table";
import { GridData } from "@/app/common/types/types";
import {
  GRID_COLUMN,
  GridAccessorReturnType,
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
  AccessorFnColumnDef<GridData, GridAccessorReturnType>["accessorFn"]
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
  MSI: "msiSession",
  PROJECT: "project",
  UPDATED_AT: "updatedAt",
};
