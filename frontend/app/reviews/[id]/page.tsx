"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API } from "@app/common/constants/api";
import { TomogramViewer, ReviewProps } from "@app/components/ViewerView/ViewerView";


export default function ReviewPage() {
    const params = useParams();
    const [review, setReview] = useState<ReviewProps | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchReview = async () => {
            try {
                const response = await fetch(`${API.REVIEWS}/${params.id}`);
                const data = await response.json();
                setReview(data);
            } catch (error) {
                console.error("Error fetching review:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchReview();
    }, [params.id]);

    if (loading) {
        return <div>Loading...</div>;
    }

    return <TomogramViewer review={review} />;
}