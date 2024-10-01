import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids/useFetchGrids";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters/useFetchFilters";
import { useContext } from "react";
import {
  buildFilterListSearchParam,
  buildGridListSearchParam,
} from "@/views/GridsView/components/Main/utils";
import { StateContext } from "@/views/GridsView/common/store";
import { State } from "@/views/GridsView/common/store/types";

export const useConnect = () => {
  const state = useContext<State>(StateContext);
  const gridList = useFetchGrids(buildGridListSearchParam(state));
  const filtersList = useFetchFilters(buildFilterListSearchParam(state));
  return { gridList, filtersList };
};
