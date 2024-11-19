export type SearchParam = Partial<
  Record<SEARCH_PARAM_NAME, SearchParamValue[]>
>;

export enum SEARCH_PARAM_NAME {
  QUERY = "q",
}

export interface SearchParamValue {
  category: string;
  value: unknown;
}
