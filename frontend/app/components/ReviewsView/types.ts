import { EntityLinkField } from "@app/common/types/entity";

export interface ReviewData {
  reviews: EntityLinkField;
  procPlan: EntityLinkField;
  json: null;
  project: EntityLinkField;
  metadata_url: string | null;
}
