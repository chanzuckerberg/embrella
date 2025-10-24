export interface Project {
    pk: number;
    model: string;
    fields: {
      name: string;
      description: string;
      project_leader: number | null;
      confluence_space: number | null;
      google_drive_folder: number | null;
    };
  }
  
  export interface ProjectsListResponse extends Array<Project> {}
  
  export interface ProjectData {
    id: number;
    name: string;
    description: string;
    projectLeader: number | null;
    confluenceSpace: number | null;
    googleDriveFolder: number | null;
  }
  
  export const transformProject = (project: Project): ProjectData => ({
    id: project.pk,
    name: project.fields.name,
    description: project.fields.description,
    projectLeader: project.fields.project_leader,
    confluenceSpace: project.fields.confluence_space,
    googleDriveFolder: project.fields.google_drive_folder,
  });