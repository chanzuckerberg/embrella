import { FiltersList, GridFilterCategory } from "@/common/types";
import { OnFilterFn } from "@/components/Filter/common/types";

export interface Props {
  filtersList?: FiltersList<GridFilterCategory>;
  onFilter: OnFilterFn;
}
