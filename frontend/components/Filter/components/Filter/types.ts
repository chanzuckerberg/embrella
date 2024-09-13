import { FilterView, OnFilterFn } from "@/components/Filter/common/types";

export interface Props<FilterId, FilterCategory extends string> {
  filterView: FilterView<FilterId, FilterCategory>;
  onFilter: OnFilterFn;
}
