'use client';

import { useParams } from 'next/navigation';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { TomogramViewerView } from '@app/components/TomogramViewerView/TomogramViewerView';
import { API } from '@app/common/constants/api';
import { Review } from '@app/components/TomogramViewerView/types';

type ReviewParams = {
  id: string;
};

export default function ReviewPage() {
  const params = useParams<ReviewParams>();
  const { data: review, isSuccess } = useFetchData<Review>(`${API.REVIEWS}${params.id}`);

  if (review === undefined) {
    return <div>Loading review...</div>;
  }

  if (!isSuccess || !review) {
    return <div>No review data available</div>;
  }

  return <TomogramViewerView review={review} />;
}
