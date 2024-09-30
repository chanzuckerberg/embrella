import {
  ActionKind,
  UpdateFilterAction,
  UpdateFilterPayload,
  UpdateSortAction,
  UpdateSortPayload,
} from "@/views/GridsView/common/store/actions/types";

/**
 * Update filter action.
 * @param payload - Payload.
 * @returns Action.
 */
export function updateFilter(payload: UpdateFilterPayload): UpdateFilterAction {
  return {
    payload,
    type: ActionKind.UpdateFilterAction,
  };
}

/**
 * Update sort action.
 * @param payload - Payload.
 * @returns Action.
 */
export function updateSort(payload: UpdateSortPayload): UpdateSortAction {
  return {
    payload,
    type: ActionKind.UpdateSortAction,
  };
}
