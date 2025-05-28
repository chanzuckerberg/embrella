'use client';

import { useParams } from 'next/navigation';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { TomogramViewerView } from '@app/components/TomogramViewerView/TomogramViewerView';
import { API } from '@app/common/constants/api';
import { Review } from '@app/components/TomogramViewerView/types';
import { useState } from 'react';

type ReviewParams = {
  id: string;
};

export default function ReviewPage() {
  const params = useParams<ReviewParams>();
  const { data: initialReview, isSuccess } = useFetchData<Review>(`${API.REVIEWS}${params.id}`);
  const [review, setReview] = useState<Review | undefined>(initialReview);

  // Update local state when initial data is loaded
  if (initialReview && !review) {
    setReview(initialReview);
  }

  if (review === undefined) {
    return <div>Loading review...</div>;
  }

  if (!isSuccess || !review) {
    return <div>No review data available</div>;
  }

  const handleReviewUpdate = (updatedReview: Review) => {
    setReview(updatedReview);
  };

  return <TomogramViewerView review={review} onReviewUpdate={handleReviewUpdate} />;
}
