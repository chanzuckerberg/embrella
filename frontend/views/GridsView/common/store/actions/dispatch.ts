import {
  ActionKind,
  UpdateFilterAction,
  UpdateFilterPayload,
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
