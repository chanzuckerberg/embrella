import { Props } from "@/components/Filter/components/Filter/types";
import { ComplexFilter as SDSComplexFilter } from "@czi-sds/components";
import {
  COMPLEX_FILTER_PROPS,
  INPUT_DROPDOWN_PROPS,
} from "@/components/Filter/components/Filter/constants";
import { MouseEvent, useCallback } from "react";
import { AutocompleteOption } from "@/components/Filter/common/types";
import { getFilterValue } from "@/components/Filter/components/Filter/utils";

export const Filter = <FilterId, FilterCategory extends string>({
  filterView,
  onFilter,
}: Props<FilterId, FilterCategory>): JSX.Element => {
  const onChange = useCallback(
    (_: MouseEvent, options: AutocompleteOption[]) => {
      onFilter({
        category: filterView.category,
        value: getFilterValue(options),
      });
    },
    [filterView, onFilter],
  );
  return (
    <SDSComplexFilter
      {...COMPLEX_FILTER_PROPS}
      DropdownMenuProps={{ onChange }}
      InputDropdownProps={{
        ...INPUT_DROPDOWN_PROPS,
        disabled: filterView.disabled,
      }}
      label={filterView.label}
      onChange={() => {}}
      options={filterView.options}
      value={filterView.value}
    />
  );
};
