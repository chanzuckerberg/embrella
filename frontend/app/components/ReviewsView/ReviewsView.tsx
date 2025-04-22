import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { API } from "@app/common/constants/api";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { REVIEW_COLUMN_IDS } from "./constants/columns";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@tremor/react";
import Link from "next/link";

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

// Define column definitions for the reviews table
const REVIEW_COLUMN_DEFS: ColumnDef<ReviewData>[] = [
  {
    id: REVIEW_COLUMN_IDS.REVIEW_NAME,
    header: "Review Name",
    accessorKey: "reviewName",
  },
  {
    id: REVIEW_COLUMN_IDS.REVIEW_TYPE,
    header: "Review Type",
    accessorKey: "reviewType",
    cell: ({ row }) => {
      const reviewType = row.original.reviewType;
      return reviewType === "tomogram_quality"
        ? "Tomogram Quality"
        : reviewType;
    },
  },
  {
    id: REVIEW_COLUMN_IDS.PROCESSING_SESSION,
    header: "Processing Session",
    accessorKey: "sessionId",
  },
  {
    id: REVIEW_COLUMN_IDS.UPDATED_AT,
    header: "Updated At",
    accessorKey: "updatedAt",
    cell: ({ row }) => {
      // Format date for display
      const date = new Date(row.original.updatedAt);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    },
  },
  {
    id: REVIEW_COLUMN_IDS.STATUS,
    header: "Status",
    accessorKey: "status",
    cell: ({ row }) => {
      const status = row.original.status;
      const statusText =
        status.charAt(0).toUpperCase() + status.slice(1).replace("_", " ");

      // Add progress info for in_progress reviews
      if (status === "in_progress") {
        const { reviewedCount, totalCount } = row.original;
        return `${statusText} (${reviewedCount}/${totalCount})`;
      }

      return statusText;
    },
  },
  {
    id: REVIEW_COLUMN_IDS.REVIEWER,
    header: "Reviewer",
    accessorKey: "reviewer",
    cell: ({ row }) => row.original.reviewer.name,
  },
  {
    id: REVIEW_COLUMN_IDS.GO_TO_REVIEW,
    header: "Actions",
    cell: ({ row }) => {
      return (
        <Link href={`/reviews/${row.original.reviewId}`} passHref>
          <Button size="xs" color="blue">
            Go to Review
          </Button>
        </Link>
      );
    },
  },
];

export const ReviewsView = () => {
  return (
    <TableStateProvider
      initialSortState={[{ desc: true, id: REVIEW_COLUMN_IDS.UPDATED_AT }]}
    >
      <FilterableTableMain>
        <TableWrapper>
          <EntityTable
            entityApi={API.GET_REVIEWS}
            entityApiResponseField="data"
            columnDefs={REVIEW_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
