import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { API } from "@app/common/constants/api";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { REVIEW_COLUMN_DEFS, REVIEW_COLUMN_IDS } from "./constants/columns";

// Define the review data interface based on the API response format
interface ReviewData {
  reviewId: string;
  reviewName: string;
  reviewType: string;
  sessionId: string;
  runId: string;
  updatedAt: string;
  status: "not_started" | "in_progress" | "complete";
  reviewedCount: number;
  totalCount: number;
  reviewer: {
    id: string;
    name: string;
  };
}

export const ReviewsView = () => {
  return (
    <TableStateProvider
      initialSortState={[{ desc: true, id: REVIEW_COLUMN_IDS.UPDATED_AT }]}
    >
      <FilterableTableMain>
        <TableWrapper>
          <EntityTable
            entityApi={API.REVIEWS}
            entityApiResponseField="reviews"
            columnDefs={REVIEW_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
