export interface UseFetchGridsOptions {
  pagination?: {
    page: number;
    pageSize: number;
  };
  sort?: {
    ascending: boolean;
    column: string;
  };
}
