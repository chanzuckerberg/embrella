import { State } from "@/views/GridsView/common/store/types";
import { GRID_COLUMN_ID } from "@/views/GridsView/components/Main/components/GridList/columns/constants";

export const DEFAULT_PAGE_SIZE = 10;

export const INITIAL_STATE: State = {
  filterState: {},
  paginationState: {
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  },
  sortState: [{ desc: true, id: GRID_COLUMN_ID.UPDATED_AT as string }],
};
