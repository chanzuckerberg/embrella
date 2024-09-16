import { FilterView, OnFilterFn } from "@/components/Filter/common/types";

export interface Props<FilterId, FilterCategory extends string> {
  className?: string;
  filters: FilterView<FilterId, FilterCategory>[][];
  onFilter: OnFilterFn;
}
