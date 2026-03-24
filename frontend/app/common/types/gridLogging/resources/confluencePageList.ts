export interface ConfluencePage {
  id: number;
  name: string;
  url: string;
  system_name?: string;
  page_id?: string;
}

export interface ConfluencePageListResponse {
  pages: ConfluencePage[];
  total_count: number;
}
