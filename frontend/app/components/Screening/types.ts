import { EntityLinkField } from '@app/common/types/entity';

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
