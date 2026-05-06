export interface ScreeningLabel {
  id: number;
  name: string;
  color: string;
}

export interface ScreeningGridData {
  grid: { id: number; name: string; updatedAt: string | null };
  project_name: string | null;
  specimen_name: string | null;
  user_name: string | null;
  clipped: boolean;
  freezing_session: { id: number; name: string; url: string } | null;
  labels: ScreeningLabel[];
}
