import { GridDetailsResponse } from '@app/common/types/gridLogging/details/gridDetails';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';

// Subset of editable grid fields sent as the PATCH/PUT payload when saving changes.
export interface EditedData {
  gridName: string;
  copyNumber: number;
  notes: string;
  freezingSessionId: number | null;
  specimenId: number | null;
  projectId: number | null;
  positionInBox: number;
  blotTime: number;
  blotForce: number;
  blotDistance: number;
}

// Full form state for the grid detail dialog, including read-only display fields and labels.
export interface GridFormData {
  gridName: string;
  user: string;
  notes: string;
  clipped: boolean;
  trashed: boolean;
  positionInBox: number;
  copyNumber: number;
  freezingSession: string;
  freezingSessionId: number | null;
  specimen: string;
  specimenId: number | null;
  project: string;
  projectId: number | null;
  blotTime: number;
  blotForce: number;
  blotDistance: number;
  labels: LabelData[];
}

export const mapGridDetailsToFormData = (data: GridDetailsResponse): GridFormData => ({
  gridName: data.grid_name || '',
  user: data.user || '',
  notes: data.notes || '',
  clipped: data.clipped || false,
  trashed: data.trashed || false,
  positionInBox: data.position_in_box || 1,
  copyNumber: data.copy_number || 1,
  freezingSession: data.freezing_session?.name || '',
  freezingSessionId: data.freezing_session?.id || null,
  specimen: data.specimen?.name || '',
  specimenId: data.specimen?.id || null,
  project: data.project?.name || '',
  projectId: data.project?.id || null,
  blotTime: data.parameters?.blot_time || 0,
  blotForce: data.parameters?.blot_force || 0,
  blotDistance: data.parameters?.blot_distance || 0,
  labels: data.labels ?? [],
});
