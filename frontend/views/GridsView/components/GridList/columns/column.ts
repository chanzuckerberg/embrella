import {
  GRID_COLUMN,
  GridColumnDef,
  GridColumnDefCellContext,
} from "@/views/GridsView/components/GridList/columns/types";
import { Links } from "@/components/Table/components/CellComponent/components/Links";
import { Link } from "@/components/Table/components/CellComponent/components/Link";
import {
  GRID_COLUMN_ACCESSOR_FN,
  GRID_COLUMN_ID,
} from "@/views/GridsView/components/GridList/columns/constants";
import { LinkTValue } from "@/components/Table/components/CellComponent/types";

export const GRID_COLUMN_DEF_CRYOGRID: GridColumnDef = {
  accessorFn: GRID_COLUMN_ACCESSOR_FN.CRYOGRID,
  cell: (props: GridColumnDefCellContext<LinkTValue>) => Link({ ...props }),
  enableSorting: false,
  id: GRID_COLUMN_ID.CRYOGRID,
  header: "Cryogrid",
};

export const GRID_COLUMN_DEF_FREEZING_PLAN: GridColumnDef = {
  accessorFn: GRID_COLUMN_ACCESSOR_FN.FREEZING_PLAN,
  cell: (props: GridColumnDefCellContext<LinkTValue[]>) => Links({ ...props }),
  enableSorting: false,
  id: GRID_COLUMN_ID.FREEZING_PLAN,
  header: "Freezing Plan",
};

export const GRID_COLUMN_DEF_FREEZING_SESSION: GridColumnDef = {
  accessorFn: GRID_COLUMN_ACCESSOR_FN.FREEZING_SESSION,
  enableSorting: false,
  id: GRID_COLUMN_ID.FREEZING_SESSION,
  header: "Freezing Session",
};

export const GRID_COLUMN_DEF_MSI: GridColumnDef = {
  accessorFn: GRID_COLUMN_ACCESSOR_FN.MSI,
  cell: (props: GridColumnDefCellContext<LinkTValue[]>) => Links({ ...props }),
  enableSorting: false,
  id: GRID_COLUMN_ID.MSI,
  header: "MSI",
};

export const GRID_COLUMN_DEF_PROJECT: GridColumnDef = {
  accessorFn: GRID_COLUMN_ACCESSOR_FN.PROJECT,
  cell: (props: GridColumnDefCellContext<LinkTValue>) => Link({ ...props }),
  enableSorting: false,
  id: GRID_COLUMN_ID.PROJECT,
  header: "Project",
};

export const GRID_COLUMN_DEF: Record<keyof typeof GRID_COLUMN, GridColumnDef> =
  {
    CRYOGRID: GRID_COLUMN_DEF_CRYOGRID,
    FREEZING_PLAN: GRID_COLUMN_DEF_FREEZING_PLAN,
    FREEZING_SESSION: GRID_COLUMN_DEF_FREEZING_SESSION,
    MSI: GRID_COLUMN_DEF_MSI,
    PROJECT: GRID_COLUMN_DEF_PROJECT,
  };

export const GRID_COLUMN_DEFS: GridColumnDef[] = [
  GRID_COLUMN_DEF.CRYOGRID,
  GRID_COLUMN_DEF.PROJECT,
  GRID_COLUMN_DEF.FREEZING_PLAN,
  GRID_COLUMN_DEF.MSI,
  GRID_COLUMN_DEF.FREEZING_SESSION,
];
