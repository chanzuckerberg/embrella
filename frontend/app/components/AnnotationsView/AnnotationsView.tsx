"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import {
  ANNOTATION_COLUMN_DEFS,
  ANNOTATION_COLUMN_IDS,
} from "./constants/columns";
import { SortingState } from "@tanstack/react-table";
import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { API } from "@app/common/constants/api";
import { AnnotationFilterId, AnnotationFilterCategory } from "./types";
import { ANNOTATION_FILTER_CONFIGS } from "./constants/filters";
import { EntityTableFilters } from "@/app/common/components/EntityTableFilters/EntityTableFilters";

export const AnnotationsView = (): React.JSX.Element => {
  const initialSortState: SortingState = [
    { desc: true, id: ANNOTATION_COLUMN_IDS.CREATED_AT },
  ];

  return (
    <TableStateProvider initialSortState={initialSortState}>
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<AnnotationFilterId, AnnotationFilterCategory>
            entityFilterConfigs={ANNOTATION_FILTER_CONFIGS}
            entityFilterListApi={API.TOMOGRAMS_FILTERLIST_V1}
          />
        </Sidebar>
        <TableWrapper>
          <EntityTable
            entityApi={API.ANNOTATIONS_V1}
            entityApiResponseField="annotations"
            columnDefs={ANNOTATION_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
