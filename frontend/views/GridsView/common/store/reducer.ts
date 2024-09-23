import { State } from "@/views/GridsView/common/store/types";
import {
  Action,
  ActionKind,
} from "@/views/GridsView/common/store/actions/types";
import { updateFilterAction } from "@/views/GridsView/common/store/actions";

/**
 * Grid list reducer.
 * @param state - State.
 * @param action - Action.
 * @returns state.
 */
export function reducer(state: State, action: Action): State {
  const { payload, type } = action;
  // eslint-disable-next-line sonarjs/no-small-switch -- TODO(cc) add pagination, sorting, etc. cases.
  switch (type) {
    case ActionKind.UpdateFilterAction: {
      return updateFilterAction(state, payload);
    }
    default:
      return state;
  }
}
