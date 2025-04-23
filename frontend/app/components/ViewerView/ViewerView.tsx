"use client";

import { Button } from "@czi-sds/components";
import Link from "next/link";

export interface ReviewProps {
    id: string;
    name: string;
    type: string;
    // Add other review fields as needed
}

export interface TomogramViewerProps {
    review: ReviewProps | null;
}

export const TomogramViewer = ({ review }: TomogramViewerProps) => {
    return (
        <div style={{ padding: '24px' }}>
            <Link href="/reviews">
                <Button size="small" color="primary" style={{ marginBottom: '16px' }}>
                    Back to Reviews
                </Button>
            </Link>
            <div style={{ marginBottom: '16px' }}>
                <h1>{review && review.name}</h1>
                <div>Type: {review && review.type}</div>
            </div>
            <div>
            </div>
        </div>
    );
};