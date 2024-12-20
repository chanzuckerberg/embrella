import React, { Fragment } from "react";
import { FilterDivider, StyledFilters } from "./style";
import { Props } from "@app/common/components/Filter/components/Filters/types";
import { Filter } from "@app/common/components/Filter/components/Filter";

export const Filters = <FilterId, FilterCategory extends string>({
  className,
  dataTestId,
  filters,
  onFilter,
}: Props<FilterId, FilterCategory>): JSX.Element => {
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
