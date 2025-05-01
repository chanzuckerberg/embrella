export type SearchParam = Partial<Record<SEARCH_PARAM_NAME, SearchParamValue[]>>;

export enum SEARCH_PARAM_NAME {
  QUERY = 'q',
  // Adding ?enable=yourFlag or ?disable=yourFlag will record your setting in cookies.
  ENABLE_FEATURE_FLAG = 'enable',
  DISABLE_FEATURE_FLAG = 'disable',
}

export interface SearchParamValue {
  category: string;
  value: unknown;
}
