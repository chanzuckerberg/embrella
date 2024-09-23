"use client";
import React, { useReducer } from "react";
import { reducer } from "@/views/GridsView/common/store/reducer";
import { INITIAL_STATE } from "@/views/GridsView/common/store/constants";
import { DispatchContext, StateContext } from "@/views/GridsView/common/store";
import { Main } from "@/views/GridsView/components/Main";

export const GridsView = (): JSX.Element => {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  return (
    <DispatchContext.Provider value={dispatch}>
      <StateContext.Provider value={state}>
        <Main />
      </StateContext.Provider>
    </DispatchContext.Provider>
  );
};
