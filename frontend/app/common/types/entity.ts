import { AnnotationData } from '@app/components/AnnotationsView/types';
import { GridData } from '@app/components/GridsView/types';
import { ReviewData } from '@app/components/ReviewsView/types';
import { TomogramData } from '@app/components/TomogramsView/types';

export type EntityAPIPrimaryAttributeToDataType = {
  annotations: AnnotationData;
  tomograms: TomogramData;
  grid: GridData;
  review: ReviewData;
};

export interface EntityLinkField {
  id: number;
  name: string;
  url: string;
}

export interface MSISessionField {
  id: number;
  name: string;
  url: string;
}

export interface GridField {
  id: number;
  name: string;
  trashed: boolean;
  url: string;
  createdAt: string;
}

export interface ProcRunField {
  id: number;
  notes: string;
  updatedAt: string;
}

export interface UserField {
  id: number;
  name: string;
}
