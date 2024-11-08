import { FilterView, OnFilterFn } from "@/app/components/Filter/common/types";

export interface Props<FilterId, FilterCategory extends string> {
  category: FilterCategory;
  filterView: FilterView<FilterId, FilterCategory>;
  onFilter: OnFilterFn<FilterCategory>;
}
