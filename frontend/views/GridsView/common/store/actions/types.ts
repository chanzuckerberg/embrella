import { CategoryFilter } from "@/components/Filter/common/types";
import {
  FiltersList,
  GridData,
  GridFilterCategory,
  SortBy,
} from "@/common/types";
import { SortingState, Updater } from "@tanstack/react-table";

export type Action = UpdateFilterAction | UpdateSortAction;

export enum ActionKind {
  UpdateFilterAction = "UPDATE_FILTER_ACTION",
  UpdateSortAction = "UPDATE_SORT_ACTION",
}

export type UpdateFilterAction = {
  payload: UpdateFilterPayload;
  type: ActionKind.UpdateFilterAction;
};

export type UpdateSortAction = {
  payload: UpdateSortPayload;
  type: ActionKind.UpdateSortAction;
};

export interface UpdateFilterPayload {
  categoryFilter: CategoryFilter<GridFilterCategory>;
  filtersList?: FiltersList<GridFilterCategory>;
}

export interface UpdateSortPayload {
  sortBy?: SortBy<GridData>;
  updaterOrValue: Updater<SortingState>;
}
