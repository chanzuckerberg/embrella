import { ColumnDef } from "@tanstack/react-table";

import { AccessorReturnType } from "@app/common/components/EntityTable/types";
import { humanize } from "@app/common/utils/string";
import { EntityDataTypes } from "@app/common/types/tableState";
import {
  LinkCellProps,
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
} from "@app/components/Table/components/LinkCell/LinkCell";
import { TomogramData } from "@app/components/TomogramsView/types";

export const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAMS: "tomograms",
  PROC_PLAN: "procPlan",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
  UPDATED_AT: "updatedAt",
};

export const TOMOGRAM_COLUMN_DEFS: ColumnDef<
  EntityDataTypes,
  AccessorReturnType
>[] = [
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAMS,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).tomograms),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.TOMOGRAMS),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROC_PLAN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).procPlan),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROC_PLAN),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).msiSession),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: "MSI Session",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).project),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROJECT),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).grid),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.GRID),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.NOTES,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as TomogramData).procRun.notes,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.NOTES),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.UPDATED_AT,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as TomogramData).procRun.updatedAt,
    enableSorting: true,
    header: humanize(TOMOGRAM_COLUMN_IDS.UPDATED_AT),
  },
];
