export interface ConfluencePage {
    id: number;
    name: string;
    url: string;
  }
  
  export interface ConfluencePageListResponse {
    pages: ConfluencePage[];
    total_count: number;
  }