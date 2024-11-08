import { CategoryFilter } from "@/app/components/Filter/common/types";
import {
  FiltersList,
  GridFilterCategory,
  Pagination,
  SortBy,
} from "@/app/common/types/types";
import { PaginationState, SortingState, Updater } from "@tanstack/react-table";

export type Action =
  | UpdateFilterAction
  | UpdatePaginationAction
  | UpdateSortAction;

export enum ActionKind {
  UpdateFilterAction = "UPDATE_FILTER_ACTION",
  UpdatePaginationAction = "UPDATE_PAGINATION_ACTION",
  UpdateSortAction = "UPDATE_SORT_ACTION",
}

export type UpdateFilterAction = {
  payload: UpdateFilterPayload;
  type: ActionKind.UpdateFilterAction;
};

export type UpdatePaginationAction = {
  payload: UpdatePaginationPayload;
  type: ActionKind.UpdatePaginationAction;
};

export type UpdateSortAction = {
  payload: UpdateSortPayload;
  type: ActionKind.UpdateSortAction;
};

export interface UpdateFilterPayload {
  categoryFilter: CategoryFilter<GridFilterCategory>;
  filtersList?: FiltersList<GridFilterCategory>;
}

export interface UpdatePaginationPayload {
  pagination?: Pagination;
  updaterOrValue: Updater<PaginationState>;
}

export interface UpdateSortPayload {
  sortBy?: SortBy;
  updaterOrValue: Updater<SortingState>;
}
