import { CreateReviewView } from "@app/components/CreateReviewView/CreateReviewView";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Embrella Review",
};

export default function CreateReviewPage() {
  return <CreateReviewView />;
}
