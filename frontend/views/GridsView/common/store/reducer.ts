import { State } from "@/views/GridsView/common/store/types";
import {
  updateFilterAction,
  updatePaginationAction,
  updateSortAction,
} from "@/views/GridsView/common/store/actions";
import {
  Action,
  ActionKind,
} from "@/views/GridsView/common/store/actions/types";

/**
 * Grid list reducer.
 * @param state - State.
 * @param action - Action.
 * @returns state.
 */
export function reducer(state: State, action: Action): State {
  const { payload, type } = action;
  switch (type) {
    case ActionKind.UpdateFilterAction: {
      return updateFilterAction(state, payload);
    }
    case ActionKind.UpdatePaginationAction: {
      return updatePaginationAction(state, payload);
    }
    case ActionKind.UpdateSortAction: {
      return updateSortAction(state, payload);
    }
    default:
      return state;
  }
}
