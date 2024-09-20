import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids";
import { UseGridList } from "@/views/GridsView/hooks/useGridList/types";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters";
import { useCallback } from "react";

export const useGridList = (): UseGridList => {
  const grids = useFetchGrids();
  const filtersList = useFetchFilters();

  const onFilter = useCallback((): void => {
    // TODO(cc): Implement filter logic.
  }, []);

  const gridList = grids?.grids;
  return { gridList, filtersList, onFilter };
};
