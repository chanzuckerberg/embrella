import { FilterView } from "@app/common/components/EntityTableFilters/types";

export type UseFilterList<FilterId, FilterCategory extends string> = FilterView<
  FilterId,
  FilterCategory
>[][];
