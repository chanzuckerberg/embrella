import { AnnotationData } from '@app/components/AnnotationsView/types';
import { GridBoxData } from '@app/components/GridInventory/GridBoxesView/types';
import { PuckData } from '@app/components/GridInventory/PucksView/types';
import { StandardSampleData } from '@app/components/StandardSamples/types';
import { GridData } from '@app/components/GridsView/types';
import { ReviewData } from '@app/components/ReviewsView/types';
import { SessionOverviewData } from '@app/components/SessionBrowserView/types';
import { TomogramData } from '@app/components/TomogramsView/types';
import { Job } from '@app/processing/jobs/monitor/types';

export type EntityAPIPrimaryAttributeToDataType = {
  annotations: AnnotationData;
  tomograms: TomogramData;
  grid: GridData;
  gridBox: GridBoxData;
  puck: PuckData;
  review: ReviewData;
  job: Job;
  session: SessionOverviewData;
  specimen: StandardSampleData;
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
