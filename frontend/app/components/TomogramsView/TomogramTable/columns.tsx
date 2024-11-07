import { Link } from "@czi-sds/components";
import { CellContext, ColumnDef } from "@tanstack/react-table";

import { TomogramData } from "@/app/common/types/tomogram";
import { Fragment } from "react";

/**
 * Default props to pass to SDS Link component
 */
const DEFAULT_LINK_PROPS = {
  sdsStyle: "default",
  target: "_blank",
};

/**
 * Required attributes for a model field with a link
 */
interface LinkField {
  name: string;
  url: string;
}

/**
 * Attributes to pass to SDS Link component
 */
interface LinkCellProps {
  children: string;
  href: string;
}

const getSDSLink = (props: CellContext<TomogramData, LinkCellProps>): React.JSX.Element => {
  return <Link {...DEFAULT_LINK_PROPS} {...props.getValue()} />;
};

const getLinkPropsFromLinkField = (linkField: LinkField) => {
  const { name, url } = linkField;
  return { children: name, href: url };
};

const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAM: "tomogram",
  PROC_PLAN: "procPlan",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
}

export const TOMOGRAM_COLUMN_DEFS: ColumnDef<TomogramData>[] = [
  // TODO: need to show id?
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAM,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.tomograms),
    cell: getSDSLink,
    enableSorting: false,
    header: "Tomogram",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROC_PLAN,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.procPlan),
    cell: getSDSLink,
    enableSorting: false,
    header: "Proc Plan",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.msiSession),
    cell: getSDSLink,
    enableSorting: false,
    header: "MSI Session",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.projects),
    cell: getSDSLink,
    enableSorting: false,
    header: "Project",
  },
  // TODO: need to show grid id?
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.grid),
    cell: getSDSLink,
    enableSorting: false,
    header: "Grid",
  }
  // TODO: Notes - not a link, is it from procRun?
];
