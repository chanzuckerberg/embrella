import { createContext, Dispatch } from "react";
import { INITIAL_STATE } from "./constants";
import { State } from "@/views/GridsView/common/store/types";
import { Action } from "@/views/GridsView/common/store/actions/types";

export const DispatchContext = createContext<Dispatch<Action> | null>(null);

export const StateContext = createContext<State>(INITIAL_STATE);
