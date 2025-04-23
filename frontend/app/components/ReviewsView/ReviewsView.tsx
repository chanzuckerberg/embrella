"use client";

import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { API } from "@app/common/constants/api";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { REVIEW_COLUMN_DEFS, REVIEW_COLUMN_IDS } from "./constants/columns";

export const ReviewsView = () => {
  return (
    <TableStateProvider
      initialSortState={[{ desc: true, id: REVIEW_COLUMN_IDS.UPDATED_AT }]}
    >
      <FilterableTableMain>
        <TableWrapper>
          <EntityTable
            entityApi={API.REVIEWS}
            entityApiResponseField="review"
            columnDefs={REVIEW_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
