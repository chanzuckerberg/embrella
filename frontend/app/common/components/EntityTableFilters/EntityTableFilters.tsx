import { Filters } from "@app/common/components/Filter/components/Filters/Filters";
import { TEST_IDS } from "@app/common/constants/testIds";
import { useConnect } from "./connect";
import {
  EntityFilterCategories,
  EntityFilterConfigs,
  EntityFilterIdTypes,
} from "@app/common/types/filter";
import { API } from "../../constants/api";

interface EntityTableFiltersProps {
  entityFilterConfigs: EntityFilterConfigs[][];
  entityFilterListApi: API;
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
    <Filters
      dataTestId={TEST_IDS.SIDEBAR_FILTERS}
      filters={filters}
      onFilter={onFilter}
    />
  );
};
