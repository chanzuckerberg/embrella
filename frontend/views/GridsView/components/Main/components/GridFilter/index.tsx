import React from "react";
import { Props } from "@/views/GridsView/components/Main/components/GridFilter/types";
import { Filters } from "@/components/Filter/components/Filters";
import { useConnect } from "@/views/GridsView/components/Main/components/GridFilter/connect";

export const GridFilter = ({ filtersList }: Props): JSX.Element => {
  const { filters, onFilter } = useConnect({ filtersList });
  return <Filters filters={filters} onFilter={onFilter} />;
};
