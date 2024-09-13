import React, { Fragment } from "react";
import { FilterDivider, StyledFilters } from "./style";
import { Props } from "@/components/Filter/components/Filters/types";
import { Filter } from "@/components/Filter/components/Filter";

export const Filters = <FilterId, FilterCategory extends string>({
  className,
  filters,
  onFilter,
}: Props<FilterId, FilterCategory>): JSX.Element => {
  return (
    <StyledFilters className={className}>
      {filters.map((filterViews, i) => (
        <Fragment key={i}>
          {i !== 0 && <FilterDivider />}
          {filterViews.map((filterView) => (
            <Filter
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
