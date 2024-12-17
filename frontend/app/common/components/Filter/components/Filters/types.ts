import {
  FilterView,
  OnFilterFn,
} from "@/app/common/components/Filter/common/types";

export interface Props<FilterId, FilterCategory extends string> {
  className?: string;
  dataTestId?: string;
  filters: FilterView<FilterId, FilterCategory>[][];
  onFilter: OnFilterFn<FilterCategory>;
}
