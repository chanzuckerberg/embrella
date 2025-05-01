import { ComplexFilterProps } from '@czi-sds/components';
import { FilterOption, FilterValue } from '@app/common/types/filter';

export type AutocompleteOption = Omit<FilterOption, 'name'> & { name: string };

export interface CategoryFilter<FilterCategory extends string> {
  category: FilterCategory;
  value: FilterValue[];
}

export type EntityTableComplexFilterProps = ComplexFilterProps<AutocompleteOption, true, false, false>;

export enum FILTER_VALUE {
  FALSE = 'false',
  TRUE = 'true',
  UNSPECIFIED = 'null',
}

export type FilterView<FilterId, FilterCategory extends string> = SelectFilterView<FilterId, FilterCategory>;

export type OnFilterFn<FilterCategory extends string> = (categoryFilter: CategoryFilter<FilterCategory>) => void;

export interface SelectFilterView<FilterId, FilterCategory extends string> {
  category: FilterCategory;
  disabled: boolean;
  filterId: FilterId;
  label: string;
  options: EntityTableComplexFilterProps['options'];
  value: EntityTableComplexFilterProps['value'];
}
