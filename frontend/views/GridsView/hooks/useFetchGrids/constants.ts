import { GridColumnDef } from "@/views/GridsView/components/Main/components/GridList/columns/types";

export const SORT_CATEGORY_VALUE: Record<
  Exclude<GridColumnDef["id"], undefined>,
  string
> = {
  updatedAt: "modifiedOn",
};
