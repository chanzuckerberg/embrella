import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids";
import { UseGridList } from "@/views/GridsView/hooks/useGridList/types";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters";
import { useCallback } from "react";

export const useGridList = (): UseGridList => {
  const gridList = useFetchGrids();
  const filtersList = useFetchFilters();

  const onFilter = useCallback((): void => {
    // TODO(cc): Implement filter logic.
  }, []);

  return { gridList, filtersList, onFilter };
};
