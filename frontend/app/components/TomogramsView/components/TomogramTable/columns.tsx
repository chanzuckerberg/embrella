import { Link } from "@czi-sds/components";
import { CellContext, ColumnDef } from "@tanstack/react-table";

import { TomogramData } from "@app/common/types/tomogram";

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
  id: number;
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

const getLinkPropsFromLinkField = (linkField: LinkField, showId = false) => {
  const { id, name, url } = linkField;
  // Optionally append id to link text
  const children = showId ? `${name} (id=${id})` : name;

  return { children, href: url };
};

const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAMS: "tomograms",
  PROC_PLAN: "procPlan",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
}

export const TOMOGRAM_COLUMN_DEFS: ColumnDef<TomogramData>[] = [
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAMS,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.tomograms, true),
    cell: getSDSLink,
    enableSorting: false,
    header: "Tomograms",
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
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.grid, true),
    cell: getSDSLink,
    enableSorting: false,
    header: "Grid",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.NOTES,
    accessorFn: (rowData: TomogramData): string => rowData.procRun.note,
    enableSorting: false,
    header: "Notes",
  },
];
