import { ColumnDef } from "@tanstack/react-table";

import { AccessorReturnType } from "@app/common/components/EntityTable/types";
import { EntityDataTypes } from "@app/common/types/tableState";
import {
  LinkCellProps,
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
} from "@app/components/Table/components/LinkCell/LinkCell";
import { humanize } from "@/app/common/utils/string";
import { AnnotationData } from "../types";

export const ANNOTATION_COLUMN_IDS = {
  ANNOTATIONS: "annotations",
  PROC_PLAN: "procPlan",
  INPUT_TOMORGRAM: "inputTomogram",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
  UPDATED_AT: "updatedAt",
};
export const ANNOTATION_COLUMN_DEFS: ColumnDef<
  EntityDataTypes,
  AccessorReturnType
>[] = [
  {
    id: ANNOTATION_COLUMN_IDS.ANNOTATIONS,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).annotations),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(ANNOTATION_COLUMN_IDS.ANNOTATIONS),
  },
  {
    id: ANNOTATION_COLUMN_IDS.PROC_PLAN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).procPlan),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(ANNOTATION_COLUMN_IDS.PROC_PLAN),
  },
  //TODO: need Input Tomograms column?
  {
    id: ANNOTATION_COLUMN_IDS.INPUT_TOMORGRAM,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).inputTomogram),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(ANNOTATION_COLUMN_IDS.INPUT_TOMORGRAM),
  },
  {
    id: ANNOTATION_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).msiSession),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: "MSI Session",
  },
  {
    id: ANNOTATION_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).project),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(ANNOTATION_COLUMN_IDS.PROJECT),
  },
  {
    id: ANNOTATION_COLUMN_IDS.GRID,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as AnnotationData).grid),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(ANNOTATION_COLUMN_IDS.GRID),
  },
  // {
  //   id: ANNOTATION_COLUMN_IDS.NOTES,
  //   accessorFn: (rowData: EntityDataTypes): string =>
  //     (rowData as AnnotationData).procRun.notes,
  //   enableSorting: false,
  //   header: humanize(ANNOTATION_COLUMN_IDS.NOTES),
  // },
  {
    id: ANNOTATION_COLUMN_IDS.UPDATED_AT,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as AnnotationData).annotations.updatedAt,
    enableSorting: true,
    header: humanize(ANNOTATION_COLUMN_IDS.UPDATED_AT),
  },
];
