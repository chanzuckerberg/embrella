import { FilterState } from "@/app/components/Filter/common/types";
import { GridFilterCategory } from "@/app/common/types/types";
import { PaginationState, SortingState } from "@tanstack/react-table";

export interface State {
  filterState: FilterState<GridFilterCategory>;
  paginationState: PaginationState;
  sortState: SortingState;
}
