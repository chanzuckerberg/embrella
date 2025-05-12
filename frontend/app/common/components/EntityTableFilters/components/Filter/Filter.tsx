import React, { useCallback } from 'react';

import { ComplexFilter, InputDropdownProps } from '@czi-sds/components';

import {
  AutocompleteOption,
  EntityTableComplexFilterProps,
  FilterView,
  OnFilterFn,
} from '@app/common/components/EntityTableFilters/types';

import { getFilterValue } from '../../utils/filterValue';

interface FilterProps<FilterId, FilterCategory extends string> {
  category: FilterCategory;
  filterView: FilterView<FilterId, FilterCategory>;
  onFilter: OnFilterFn<FilterCategory>;
}

const COMPLEX_FILTER_PROPS: Pick<
  EntityTableComplexFilterProps,
  'isTriggerChangeOnOptionClick' | 'multiple' | 'search'
> = {
  isTriggerChangeOnOptionClick: true,
  multiple: true,
  search: true,
};

const INPUT_DROPDOWN_PROPS: Pick<InputDropdownProps, 'intent' | 'sdsStyle' | 'sdsType' | 'state'> = {
  intent: 'default',
  sdsStyle: 'minimal',
  sdsType: 'label',
  state: 'default',
};

export const Filter = <FilterId, FilterCategory extends string>({
  category,
  filterView,
  onFilter,
}: FilterProps<FilterId, FilterCategory>): JSX.Element => {
  const onChange = useCallback(
    (options: (string | AutocompleteOption)[]) => {
      onFilter({
        category,
        value: getFilterValue(options),
      });
    },
    [category, onFilter]
  );
  return (
    <ComplexFilter
      {...COMPLEX_FILTER_PROPS}
      InputDropdownProps={{
        ...INPUT_DROPDOWN_PROPS,
        disabled: filterView.disabled,
      }}
      label={filterView.label}
      onChange={onChange}
      options={filterView.options}
      value={filterView.value}
    />
  );
};
