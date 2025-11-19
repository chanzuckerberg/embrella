export interface ConfluenceSpace {
    id: number;
    name: string;
    space_id: string;
    url: string;
  }
  
  export interface ConfluenceSpaceListResponse {
    spaces: ConfluenceSpace[];
    total_count: number;
  }