export interface FetchResponseInfo {
  status?: number;
  body?: string | ((u: URL) => string);
}

export type TestResponse = Pick<Response, "json" | "text" | "status">;
