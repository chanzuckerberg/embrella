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

type AccessorReturnType = LinkCellProps | string;

const getLinkPropsFromLinkField = (linkField: LinkField) => ({
  children: linkField.name,
  href: linkField.url,
});

const getSDSLink = (props: CellContext<TomogramData, LinkCellProps>): React.JSX.Element => (
  <Link {...DEFAULT_LINK_PROPS} {...props.getValue()} />
);

const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAMS: "tomograms",
  PROC_PLAN: "procPlan",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
  CREATED_AT: "createdAt",
}

export const TOMOGRAM_COLUMN_DEFS: ColumnDef<TomogramData, AccessorReturnType>[] = [
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAMS,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.tomograms),
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
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.project),
    cell: getSDSLink,
    enableSorting: false,
    header: "Project",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: TomogramData): LinkCellProps => getLinkPropsFromLinkField(rowData.grid),
    cell: getSDSLink,
    enableSorting: false,
    header: "Grid",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.NOTES,
    accessorFn: (rowData: TomogramData): string => rowData.procRun.notes,
    enableSorting: false,
    header: "Notes",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.CREATED_AT,
    accessorFn: (rowData: TomogramData): string => rowData.procRun.createdAt,
    enableSorting: true,
    header: "Created At",
  },
];
