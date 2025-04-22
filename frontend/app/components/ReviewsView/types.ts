import { EntityLinkField } from "@app/common/types/entity";

export interface Review extends EntityLinkField {
  type: string;
}

export interface ReviewData {
  review: Review;
  session: EntityLinkField;
  updatedAt: string;
  status: string;
  reviewer: EntityLinkField;
}
