import { ReviewsView } from "@app/components/ReviewsView/ReviewsView";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Embrella Reviews",
};

const ReviewsPage = () => {
  return <ReviewsView />;
};

export default ReviewsPage;
