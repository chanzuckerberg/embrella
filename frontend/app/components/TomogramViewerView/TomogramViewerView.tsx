"use client";

import { Button } from "@czi-sds/components";
import Link from "next/link";

export interface User {
    id: string | number;  // Can be UUID or number
    name: string;
}

export interface ReviewTomogramSummary {
    tomogramId: string;
    status: "pending" | "accepted" | "rejected" | "uncertain";
}

export interface Review {
    reviewId: string;  // UUID
    reviewName: string;
    owner: User;
    tomograms: ReviewTomogramSummary[];
}

export interface TomogramViewerProps {
    review: Review;
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
                <h1>{review.reviewName}</h1>
                <div>Owner: {review.owner.name}</div>
                <div style={{ marginTop: '24px' }}>
                    <h2>Tomograms</h2>
                    <div>
                        {review.tomograms.map((tomogram) => (
                            <div
                                key={tomogram.tomogramId}
                                style={{
                                    marginBottom: '8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}
                            >
                                <div>ID: {tomogram.tomogramId}</div>
                                <div>Status: {tomogram.status}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};