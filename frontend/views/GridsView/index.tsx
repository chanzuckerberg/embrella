"use client";
import React from "react";
import { GridList } from "@/views/GridsView/components/GridList";
import { GRIDS } from "@/views/GridsView/common/constants";

export const GridsView = (): JSX.Element => {
  return <GridList grids={GRIDS} />;
};
