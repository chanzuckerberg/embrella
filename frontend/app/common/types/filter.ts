import { GridFilterCategory } from "./types";
import { TomogramFilterCategory } from "@app/components/TomogramsView/types";

export interface FiltersList {
  filters: Record<ViewFilterCategory, FilterOption[]>;
}

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

export type ViewFilterCategory = GridFilterCategory | TomogramFilterCategory;
