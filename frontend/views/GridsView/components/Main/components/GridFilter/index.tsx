import React from "react";
import { Props } from "@/views/GridsView/components/Main/components/GridFilter/types";
import { Filters } from "@/components/Filter/components/Filters";
import { useConnect } from "@/views/GridsView/components/Main/components/GridFilter/connect";
import { TEST_ID_GRID_FILTERS } from "@/views/GridsView/components/Main/components/GridFilter/constants";

export const GridFilter = ({ filtersList }: Props): JSX.Element => {
  const { filters, onFilter } = useConnect({ filtersList });
  return (
    <Filters
      dataTestId={TEST_ID_GRID_FILTERS}
      filters={filters}
      onFilter={onFilter}
    />
  );
};
