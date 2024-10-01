import { FilterState } from "@/components/Filter/common/types";
import { GridFilterCategory } from "@/common/types";
import { SortingState } from "@tanstack/react-table";

export interface State {
  filterState: FilterState<GridFilterCategory>;
  sortState: SortingState;
}
