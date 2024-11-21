import { GridData } from "@/app/common/types/types";
import { EntityList } from "@/app/common/types/tableState";

export interface Props {
  gridList?: EntityList<GridData, "grids">;
}
