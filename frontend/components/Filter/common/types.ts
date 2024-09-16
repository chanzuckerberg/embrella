import { ComplexFilterProps as SDSComplexFilterProps } from "@czi-sds/components";
import { FilterOption } from "@/common/types";

export type AutocompleteOption = Omit<FilterOption, "name"> & { name: string };

export interface BaseFilterConfig<FilterId, FilterCategory extends string> {
  filterCategory: FilterCategory; // Key in result set row values to filter on.
  filterId: FilterId;
  label: string;
}

export type ComplexFilterProps = SDSComplexFilterProps<
  AutocompleteOption,
  true,
  false,
  false
>;

export type FilterConfig<
  FilterId,
  FilterCategory extends string,
> = BaseFilterConfig<FilterId, FilterCategory>;

export enum FILTER_VALUE {
  UNSPECIFIED = "Unspecified",
}

export type FilterValue = string | null;

export type FilterView<
  FilterId,
  FilterCategory extends string,
> = SelectFilterView<FilterId, FilterCategory>;

export type OnFilterFn = <FilterCategory extends string>({
  category,
  value,
}: {
  category: FilterCategory;
  value: FilterValue[];
}) => void;

export interface SelectFilterView<FilterId, FilterCategory extends string> {
  category: FilterCategory;
  disabled: boolean;
  filterId: FilterId;
  label: string;
  options: ComplexFilterProps["options"];
  value: ComplexFilterProps["value"];
}
