import { State } from "@/views/GridsView/common/store/types";
import { GRID_COLUMN_ID } from "@/views/GridsView/components/Main/components/GridList/columns/constants";

export const INITIAL_STATE: State = {
  filterState: {},
  sortState: [{ desc: false, id: GRID_COLUMN_ID.UPDATED_AT as string }],
};
