import { useContext } from "react";
import {
  TableState,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { API } from "@app/common/constants/api";
import { useFetchTableData } from "@app/common/hooks/useFetchTableData/useFetchTableData";
import { SEARCH_PARAM_NAME } from "@app/common/types/search";
import {
  getFilterSearchParamValues,
  getPaginationSearchParamValues,
  getSortSearchParamValue,
} from "@app/common/utils/searchParam";

// TODO: explore moving this into EntityTable component
export const useConnect = () => {
  const state = useContext<TableState>(TableStateContext);

  const tomogramList = useFetchTableData(API.TOMOGRAMS_V1, {
    [SEARCH_PARAM_NAME.QUERY]: [
      ...getFilterSearchParamValues(state),
      ...getPaginationSearchParamValues(state),
      ...getSortSearchParamValue(state),
    ],
  });

  return { tomogramList };
};
