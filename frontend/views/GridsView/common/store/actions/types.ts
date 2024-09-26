import { CategoryFilter } from "@/components/Filter/common/types";
import { FiltersList, GridFilterCategory } from "@/common/types";

export type Action = UpdateFilterAction;

export enum ActionKind {
  UpdateFilterAction = "UPDATE_FILTER_ACTION",
}

export type UpdateFilterAction = {
  payload: UpdateFilterPayload;
  type: ActionKind.UpdateFilterAction;
};

export interface UpdateFilterPayload {
  categoryFilter: CategoryFilter<GridFilterCategory>;
  filtersList?: FiltersList<GridFilterCategory>;
}
