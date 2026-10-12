export interface Project {
  id: number;
  name: string;
  description: string;
  project_leader: number | null;
  confluence_space: number | null;
  google_drive_folder: number | null;
}

export type ProjectListResponse = Array<Project>;

export interface ProjectData {
  id: number;
  name: string;
  description: string;
  projectLeader: number | null;
  confluenceSpace: number | null;
  googleDriveFolder: number | null;
}

// Add this interface for the form data
export interface ProjectFormData {
  name: string;
  description: string;
  projectLeader: string;
  confluenceSpace: string;
  googleDriveFolder: string;
}

// For creating projects (API payload)
export interface CreateProjectData {
  name: string;
  description?: string;
  project_leader?: number | null;
  confluence_space?: number | null;
  google_drive_folder?: number | null;
}

export interface ProjectCreateResponse {
  id: number;
  name: string;
  description: string;
  project_leader: number | null;
  project_leader_name: string | null;
  confluence_space: number | null;
  confluence_space_name: string | null;
  google_drive_folder: number | null;
  google_drive_folder_name: string | null;
}

export const transformProject = (project: Project): ProjectData => ({
  id: project.id,
  name: project.name,
  description: project.description,
  projectLeader: project.project_leader,
  confluenceSpace: project.confluence_space,
  googleDriveFolder: project.google_drive_folder,
});
