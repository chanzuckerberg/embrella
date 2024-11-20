import React from "react";
import { TEST_IDS } from "@app/common/constants/testIds";
import { Filters } from "@app/components/Filter/components/Filters";
import { useConnect } from "./connect";

export const TomogramFilters = (): React.JSX.Element => {
  const { filters, onFilter } = useConnect();

  return <Filters
    dataTestId={TEST_IDS.SIDEBAR_FILTERS}
    filters={filters}
    onFilter={onFilter}
  />
};
