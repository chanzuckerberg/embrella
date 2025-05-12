export interface User {
  id: string | number;
  name: string;
}

export interface ReviewTomogramSummary {
  tomogramId: string;
  status: 'pending' | 'accepted' | 'rejected' | 'uncertain';
}

export interface ReviewTomogramDetail {
  tomogramId: string;
  displayName: string;
  zarrPath: string;
  existingReview?: {
    quality: 'accepted' | 'rejected' | 'uncertain';
    rejectionReasons?: string[];
    objectLabels?: string[];
  };
}

export interface Review {
  reviewId: string;
  reviewName: string;
  owner: User;
  tomograms: ReviewTomogramSummary[];
}
