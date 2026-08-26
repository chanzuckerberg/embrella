export interface SessionPlanOption {
  id: number;
  name: string;
}

export interface ProjectOption {
  id: number;
  name: string;
}

export interface GridOption {
  id: number;
  name: string;
  display_name: string;
  is_default: boolean;
}

export interface MagnificationOption {
  id: number;
  nominal_mag: number;
  mode: string;
  index: number;
  scope__name: string;
  display: string;
}

export interface UserOption {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
}

export interface FormOptions {
  session_plans: SessionPlanOption[];
  projects: ProjectOption[];
}

/** Where a role's data lands: the resolved directory, and the filenames expected in it. */
export interface RolePath {
  directory: string | null;
  pattern: string | null;
}

export interface CreatedSession {
  id: number;
  name: string;
  project_name: string;
  grid_name: string;
  session_plan_name: string;
  magnification_display: string | null;
  frames: RolePath;
  sums: RolePath;
  mdocs: RolePath;
  parents: RolePath;
  atlas: RolePath;
  legacy_url: string;
}

export interface SessionFormState {
  sessionPlanId: number | null;
  projectId: number | null;
  gridId: number | null;
  magnificationId: number | null;
  name: string;
  filterUserId: number | null;
}
