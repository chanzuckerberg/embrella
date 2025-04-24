"use client";

import { useParams } from "next/navigation";
import { TomogramViewer } from "@app/components/TomogramViewerView/TomogramViewerView";
import { useFetchReviewData } from "@hooks/useFetchData/useFetchData";

type ReviewParams = {
    id: string;
};

export default function ReviewPage() {
    const params = useParams<ReviewParams>();
    const { data: review, isSuccess, isLoading } = useFetchReviewData(params.id);

    if (isLoading) {
        return <div>Loading review...</div>;
    }

    if (!isSuccess || !review) {
        return <div>No review data available</div>;
    }

    return <TomogramViewer review={review} />;
}