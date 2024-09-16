"use client";
import React from "react";
import { GridList } from "@/views/GridsView/components/GridList";
import { useFetchGrids } from "./hooks/useFetchGrids";

export const GridsView = (): JSX.Element => {
  const grids = useFetchGrids()?.grids;
  return <GridList grids={grids} />;
};