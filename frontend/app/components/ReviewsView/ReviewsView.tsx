"use client";

import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { API } from "@app/common/constants/api";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { REVIEW_COLUMN_IDS } from "./constants/columns";
import { ReviewsViewHeader } from "./components/ReviewsViewHeader/ReviewsViewHeader";
import { ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";
import { ReviewData } from "./types";
import { CellLink } from "@app/common/components/EntityTable/utils/linkUtils";
import { AccessorReturnType } from "@app/common/components/EntityTable/types";
import { ReviewActionButton } from "./components/ReviewActionButton/ReviewActionButton";

const columnHelper = createColumnHelper<ReviewData>();

export const ReviewsView = () => {
  const columns = useMemo(
    () => [
      columnHelper.accessor("review.name", {
        header: "Review Name",
        cell: ({ getValue }) => <b>{getValue().toString()}</b>,
      }),
      columnHelper.accessor("review.type", {
        header: "Review Type",
      }),
      columnHelper.accessor("session", {
        header: "Processing Session",
        cell: ({ getValue }) => <CellLink linkField={getValue()} />,
      }),
      columnHelper.accessor("updatedAt", {
        header: "Updated At",
      }),
      columnHelper.display({
        header: "Status",
        cell: ({ row }) => (
          <>
            <div>{row.original.status}</div>
            <div className="text-[#6c6c6c] text-[12px]">
              {row.original.reviewedCount} of {row.original.totalCount}{" "}
              Tomograms Reviewed
            </div>
          </>
        ),
      }),
      columnHelper.accessor("reviewer.name", {
        header: "Reviewer",
      }),
      columnHelper.display({
        id: REVIEW_COLUMN_IDS.GO_TO_REVIEW,
        cell: ({ row }) => (
          <ReviewActionButton
            reviewId={row.original.review.id}
            reviewStatus={row.original.status}
            reviewer={row.original.reviewer}
          />
        ),
      }),
    ],
    [],
  );

  return (
    <TableStateProvider
      initialSortState={[{ desc: true, id: REVIEW_COLUMN_IDS.UPDATED_AT }]}
    >
      <TableWrapper>
        <ReviewsViewHeader />
        <EntityTable
          entityApi={API.REVIEWS}
          entityApiResponseField="review"
          columnDefs={
            columns as Array<ColumnDef<ReviewData, AccessorReturnType>>
          }
        />
      </TableWrapper>
    </TableStateProvider>
  );
};
