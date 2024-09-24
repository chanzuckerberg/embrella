import { GridFilterCategory } from "@/common/types";

export interface FetchResponseInfo {
  status?: number;
  body?: string | ((u: URL) => string);
}

export type TestFilterCategory = GridFilterCategory;

export type TestResponse = Pick<Response, "json" | "text" | "status" | "url">;
