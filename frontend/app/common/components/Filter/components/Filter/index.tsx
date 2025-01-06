import { Props } from "@app/common/components/Filter/components/Filter/types";
import { ComplexFilter as SDSComplexFilter } from "@czi-sds/components";
import {
  COMPLEX_FILTER_PROPS,
  INPUT_DROPDOWN_PROPS,
} from "@app/common/components/Filter/components/Filter/constants";
import React, { useCallback } from "react";
import { getFilterValue } from "@app/common/components/Filter/components/Filter/utils";
import { AutocompleteOption } from "@app/common/components/Filter/common/types";

export const Filter = <FilterId, FilterCategory extends string>({
  category,
  filterView,
  onFilter,
}: Props<FilterId, FilterCategory>): JSX.Element => {
  const onChange = useCallback(
    (options: (string | AutocompleteOption)[]) => {
      onFilter({
        category,
        value: getFilterValue(options),
      });
    },
    [category, onFilter],
  );
  return (
    <SDSComplexFilter
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
