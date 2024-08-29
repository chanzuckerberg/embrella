export interface FetchResponseInfo {
  status?: number;
  body?: string;
}

export type TestResponse = Pick<Response, "json" | "text" | "status">;
