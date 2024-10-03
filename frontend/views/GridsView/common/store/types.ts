import { FilterState } from "@/components/Filter/common/types";
import { GridFilterCategory } from "@/common/types";
import { PaginationState, SortingState } from "@tanstack/react-table";

export interface State {
  filterState: FilterState<GridFilterCategory>;
  paginationState: PaginationState;
  sortState: SortingState;
}
