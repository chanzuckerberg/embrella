import { EntityLinkField } from '@app/common/types/entity';

export interface Review extends EntityLinkField {
  type: string;
}

export interface ReviewData {
  review: Review;
  session: EntityLinkField;
  updatedAt: string;
  status: string;
  reviewedCount: number;
  totalCount: number;
  reviewer: EntityLinkField;
}

export interface TemSession {
  id: number;
  sessionName: string;
  projectName: string;
  createdAt: string;
  savePath: string;
  runs: Run[];
}

export interface Run {
  runId: string;
  numTomograms: number;
  reconstructionTypes: string[];
}

export type ReviewFilterCategory = 'search';
