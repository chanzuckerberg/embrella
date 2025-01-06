import React, { Fragment } from "react";

import {
  FilterView,
  OnFilterFn,
} from "@/app/common/components/Filter/common/types";

import { Filter } from "@/app/common/components/Filter/components/Filter/Filter";
import { FilterDivider, StyledFilters } from "./style";

interface FiltersProps<FilterId, FilterCategory extends string> {
  className?: string;
  dataTestId?: string;
  filters: FilterView<FilterId, FilterCategory>[][];
  onFilter: OnFilterFn<FilterCategory>;
}

export const Filters = <FilterId, FilterCategory extends string>({
  className,
  dataTestId,
  filters,
  onFilter,
}: FiltersProps<FilterId, FilterCategory>): JSX.Element => {
  return (
    <StyledFilters className={className} data-testid={dataTestId}>
      {filters.map((filterViews, i) => (
        <Fragment key={i}>
          {i !== 0 && <FilterDivider />}
          {filterViews.map((filterView) => (
            <Filter
              category={filterView.category}
              filterView={filterView}
              key={filterView.category}
              onFilter={onFilter}
            />
          ))}
        </Fragment>
      ))}
    </StyledFilters>
  );
};
