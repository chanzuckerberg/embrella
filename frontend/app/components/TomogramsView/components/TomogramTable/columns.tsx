import { Link } from "@czi-sds/components";
import { CellContext, ColumnDef } from "@tanstack/react-table";

import { TomogramData } from "@app/common/types/tomogram";
import { EntityDataTypes } from "@/app/common/types/tableState";

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

// TODO: move to common table types
export type AccessorReturnType = LinkCellProps | string;

const getLinkCellAccessorFn = (field: LinkField): Function => {
  return (rowData: EntityDataTypes): LinkCellProps => {
    return {
      children: field.name,
      href: field.url,
    };
  };
}
const getLinkPropsFromLinkField = (linkField: LinkField) => ({
  children: linkField.name,
  href: linkField.url,
});

const getSDSLink = (props: CellContext<TomogramData, LinkCellProps>): React.JSX.Element => (
  <Link {...DEFAULT_LINK_PROPS} {...props.getValue()} />
);

export const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAMS: "tomograms",
  PROC_PLAN: "procPlan",
  MSI_SESSION: "msiSession",
  PROJECT: "project",
  GRID: "grid",
  NOTES: "notes",
  CREATED_AT: "createdAt",
}


export const TOMOGRAM_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAMS,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).tomograms),
    cell: getSDSLink,
    enableSorting: false,
    header: "Tomograms",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROC_PLAN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).procPlan),
    cell: getSDSLink,
    enableSorting: false,
    header: "Proc Plan",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).msiSession),
    cell: getSDSLink,
    enableSorting: false,
    header: "MSI Session",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).project),
    cell: getSDSLink,
    enableSorting: false,
    header: "Project",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).grid),
    cell: getSDSLink,
    enableSorting: false,
    header: "Grid",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.NOTES,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as TomogramData).procRun.notes,
    enableSorting: false,
    header: "Notes",
  },
  {
    id: TOMOGRAM_COLUMN_IDS.CREATED_AT,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as TomogramData).procRun.createdAt,
    enableSorting: true,
    header: "Created At",
  },
];
