import { EntityLinkField } from '@app/common/types/entity';
import { FilterConfig } from '@app/common/types/filter';

export interface ScreeningLabel {
  id: number;
  name: string;
  color: string;
}

export interface ScreeningGridData {
  grid: { id: number; name: string; updatedAt: string | null };
  project: EntityLinkField | null;
  specimen_name: string | null;
  user_name: string | null;
  clipped: boolean;
  freezing_session: EntityLinkField | null;
  labels: ScreeningLabel[];
}

export enum ScreeningFilterId {
  STATUS = 'STATUS',
  MICROSCOPE = 'MICROSCOPE',
  PRIORITY = 'PRIORITY',
  PROJECT = 'PROJECT',
}

// 'screeningStatus' (not 'status') avoids colliding with the shared trashed-status category.
export type ScreeningFilterCategory = 'screeningStatus' | 'microscope' | 'priority' | 'project';

export type ScreeningFilterConfig = FilterConfig<ScreeningFilterId, ScreeningFilterCategory>;
