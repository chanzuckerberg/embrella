import { ColumnDef } from "@tanstack/react-table";
import { ReviewData } from "../types";
import Link from "next/link";
import { Button } from "@czi-sds/components";
import { AccessorReturnType } from "@app/common/components/EntityTable/types";

export const REVIEW_COLUMN_IDS = {
  REVIEW_NAME: "reviewName",
  REVIEW_TYPE: "reviewType",
  PROCESSING_SESSION: "processingSession",
  UPDATED_AT: "updatedAt",
  STATUS: "status",
  REVIEWER: "reviewer",
  GO_TO_REVIEW: "goToReview",
};

export const REVIEW_COLUMN_DEFS: ColumnDef<ReviewData, AccessorReturnType>[] = [
  {
    id: REVIEW_COLUMN_IDS.REVIEW_NAME,
    header: "Review Name",
    accessorKey: "review.name",
  },
  {
    id: REVIEW_COLUMN_IDS.REVIEW_TYPE,
    header: "Review Type",
    accessorKey: "review.type",
  },
  {
    id: REVIEW_COLUMN_IDS.PROCESSING_SESSION,
    header: "Processing Session",
    accessorKey: "session.name",
  },
  {
    id: REVIEW_COLUMN_IDS.UPDATED_AT,
    header: "Updated At",
    accessorKey: "updatedAt",
  },
  {
    id: REVIEW_COLUMN_IDS.STATUS,
    header: "Status",
    accessorKey: "status",
  },
  {
    id: REVIEW_COLUMN_IDS.REVIEWER,
    header: "Reviewer",
    accessorKey: "reviewer.name",
  },
  {
    id: REVIEW_COLUMN_IDS.GO_TO_REVIEW,
    header: "Actions",
    cell: ({ row }) => (
      <Link href={`/reviews/${row.original.review.id}`}>
        <Button size="small" color="primary">
          Go to Review
        </Button>
      </Link>
    ),
  },
];
