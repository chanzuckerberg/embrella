import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids/useFetchGrids";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters/useFetchFilters";
import { useContext, useMemo } from "react";
import {
  buildFilterSearchParam,
  buildSearchParam,
} from "@/views/GridsView/components/Main/utils";
import { StateContext } from "@/views/GridsView/common/store";
import { State } from "@/views/GridsView/common/store/types";

export const useConnect = () => {
  const { filterState } = useContext<State>(StateContext);

  // Build param "q" for filtering grid and filters list.
  const qParam = useMemo(
    () => buildFilterSearchParam(filterState),
    [filterState],
  );

  // Fetch grid and filters list.
  const gridList = useFetchGrids({}, buildSearchParam({ qParam }));
  const filtersList = useFetchFilters(buildSearchParam({ qParam }));

  return { gridList, filtersList };
};
