import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids/useFetchGrids";
import { useFetchGridsFilters } from "@/views/GridsView/hooks/useFetchGridsFilters/useFetchGridsFilters";
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
  const filtersList = useFetchGridsFilters(buildFilterListSearchParam(state));
  return { gridList, filtersList };
};
