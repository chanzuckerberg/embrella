import { EntityLinkField, GridField, MSISessionField, UserField } from '@app/common/types/entity';
import { FilterConfig } from '@app/common/types/filter';

export interface GridData {
  grid: GridField & { updatedAt: string | null };
  cassette: {
    name: string;
  };
  project: EntityLinkField;
  puck: {
    name: string;
  };
  user: UserField;
  specimen: {
    id: number;
    name: string;
    samples: EntityLinkField[];
  };
  freezingSession: {
    id: number;
    createdAt: string;
  };
  screeningSession: string;
  msiSession: MSISessionField[];
  labels: { id: number; name: string; color: string }[];
}

export enum GridFilterId {
  CASSETTE = 'CASSETTE',
  DATE = 'DATE',
  MSI_SESSION = 'MSI_SESSION',
  PROJECT = 'PROJECT',
  PUCK = 'PUCK',
  SAMPLE = 'SAMPLE',
  SCREENING_SESSION = 'SCREENING_SESSION',
  LABEL = 'LABEL',
  STATUS = 'STATUS',
  USER = 'USER',
}

export type GridFilterCategory =
  | 'cassette'
  | 'date'
  | 'label'
  | 'msiSession'
  | 'project'
  | 'puck'
  | 'sample'
  | 'screeningSession'
  | 'search'
  | 'status'
  | 'user';

export type GridFilterConfig = FilterConfig<GridFilterId, GridFilterCategory>;
