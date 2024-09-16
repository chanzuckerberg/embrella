import { FilterView } from "@/components/Filter/common/types";

export type UseFilterList<FilterId, FilterCategory extends string> = FilterView<
  FilterId,
  FilterCategory
>[][];
