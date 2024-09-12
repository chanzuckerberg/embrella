import { GridData } from "@/common/types";

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

export interface UseFetchGrids {
  grids: GridData[];
  pagination: {
    page: number;
    pageSize: number;
    totalPages: number;
    totalResults: number;
  };
}
