import { FiltersList, GridData, GridFilterCategory } from "@/common/types";

export interface UseGridList {
  gridList?: GridData[];
  filtersList?: FiltersList<GridFilterCategory>;
  onFilter: () => void; // TODO(cc): Implement filter interface.
}
