import { State } from "@/views/GridsView/common/store/types";
import { UpdateFilterPayload } from "@/views/GridsView/common/store/actions/types";
import { buildNextFilterState } from "@/components/Filter/common/utils";

/**
 * Update filter action.
 * @param state - State.
 * @param payload - Payload.
 * @returns state.
 */
export function updateFilterAction(
  state: State,
  payload: UpdateFilterPayload,
): State {
  return {
    ...state,
    filterState: buildNextFilterState(
      payload.categoryFilter,
      payload.filtersList,
    ),
  };
}
