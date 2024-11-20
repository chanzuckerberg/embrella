import { State } from "@/views/GridsView/common/store/types";
import {
  UpdateFilterPayload,
  UpdatePaginationPayload,
  UpdateSortPayload,
} from "@/views/GridsView/common/store/actions/types";
import { buildNextFilterState } from "@/views/GridsView/common/store/actions/filter";
import { buildNextSortState } from "@/views/GridsView/common/store/actions/sort";
import { buildNextPaginationState } from "@/views/GridsView/common/store/actions/pagination";

/**
 * Update filter action.
 * @param state - State.
 * @param payload - Payload.
 * @returns state.
 */
export function updateFilterAction(
  state: State,
  payload: UpdateFilterPayload
): State {
  return {
    ...state,
    filterState: buildNextFilterState(
      payload.categoryFilter,
      payload.filtersList
    ),
  };
}

/**
 * Update pagination action.
 * @param state - State.
 * @param payload - Payload.
 * @returns state.
 */
export function updatePaginationAction(
  state: State,
  payload: UpdatePaginationPayload
): State {
  return {
    ...state,
    paginationState: buildNextPaginationState(
      payload.updaterOrValue,
      payload.pagination
    ),
  };
}

/**
 * Update sort action.
 * @param state - State.
 * @param payload - Payload.
 * @returns state.
 */
export function updateSortAction(
  state: State,
  payload: UpdateSortPayload
): State {
  return {
    ...state,
    sortState: buildNextSortState(payload.updaterOrValue, payload.sortBy),
  };
}
