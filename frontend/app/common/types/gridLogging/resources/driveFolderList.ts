export interface DriveFolder {
  id: number;
  name: string;
  url: string;
}

export interface DriveFolderListResponse {
  folders: DriveFolder[];
  total_count: number;
}
