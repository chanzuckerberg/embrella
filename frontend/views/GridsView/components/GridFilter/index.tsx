import React from "react";
import { Props } from "@/views/GridsView/components/GridFilter/types";
import { useFilterList } from "@/components/Filter/hooks/useFilterList/useFilterList";
import { GRID_FILTER_CONFIGS } from "@/views/GridsView/components/GridFilter/filters/filter";
import { GRID_FILTER_ID } from "@/views/GridsView/components/GridFilter/filters/types";
import { GridFilterCategory } from "@/common/types";
import { Filters } from "@/components/Filter/components/Filters";

export const GridFilter = ({ filtersList, onFilter }: Props): JSX.Element => {
  const filters = useFilterList<GRID_FILTER_ID, GridFilterCategory>(
    GRID_FILTER_CONFIGS,
    filtersList,
  );
  return <Filters filters={filters} onFilter={onFilter} />;
};
