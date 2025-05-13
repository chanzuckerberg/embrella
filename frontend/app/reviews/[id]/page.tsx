'use client';

import { useParams } from 'next/navigation';
// import { TomogramViewer } from "@app/components/TomogramViewerView/TomogramViewerView";
import { useFetchReviewData } from '@hooks/useFetchData/useFetchData';
import { TomogramViewerView } from '@app/components/TomogramViewerView/TomogramViewerView';

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

  return <TomogramViewerView review={review} />;
}
