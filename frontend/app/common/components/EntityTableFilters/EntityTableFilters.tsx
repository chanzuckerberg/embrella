import { Fragment } from "react";

import { GET_API } from "@app/common/constants/api";
import { TEST_IDS } from "@app/common/constants/testIds";
import {
  EntityFilterCategories,
  EntityFilterConfigs,
  EntityFilterIdTypes,
} from "@app/common/types/filter";

import { Filter } from "./components/Filter/Filter";
import { useConnect } from "./connect";
import { FilterDivider, StyledFilters } from "./style";

interface EntityTableFiltersProps {
  entityFilterConfigs: EntityFilterConfigs[][];
  entityFilterListApi: GET_API;
  className?: string;
}

export const EntityTableFilters = <
  ENTITY_FILTER_ID extends EntityFilterIdTypes,
  EntityFilterCategory extends EntityFilterCategories,
>({
  entityFilterConfigs,
  entityFilterListApi,
}: EntityTableFiltersProps): React.JSX.Element => {
  const { filters, onFilter } = useConnect<
    ENTITY_FILTER_ID,
    EntityFilterCategory
  >(entityFilterConfigs, entityFilterListApi);

  return (
    <StyledFilters data-testid={TEST_IDS.SIDEBAR_FILTERS}>
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
