import configs from "@/configs/local";
import {
  ApiListResponse,
  GridData,
  SEARCH_PARAM_NAME,
  SearchParam,
} from "@/common/types";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { API } from "@/common/api";
import {
  UseFetchGrids,
  UseFetchGridsOptions,
} from "@/views/GridsView/hooks/useFetchGrids/types";

export const useFetchGrids = (
  options: UseFetchGridsOptions = {},
  searchParam: SearchParam,
): UseFetchGrids | undefined => {
  if (options.sort) {
    // TODO(cc): build sort search params in useGridList with sort state.
    searchParam[SEARCH_PARAM_NAME.SORT_COLUMN_NAME] = options.sort.column;
    searchParam[SEARCH_PARAM_NAME.SORT_DIRECTION] = options.sort.ascending
      ? "true"
      : "false";
  }
  if (options.pagination) {
    // TODO(cc): build pagination search params in useGridList with pagination state.
    searchParam[SEARCH_PARAM_NAME.PAGINATION_PAGE] = options.pagination.page;
    searchParam[SEARCH_PARAM_NAME.PAGINATION_PAGE_SIZE] =
      options.pagination.pageSize;
  }
  const { data: gridsData } = useFetchData<ApiListResponse<GridData>>(
    configs.API_URL,
    API.GRIDS,
    searchParam,
  );
  return (
    gridsData && {
      grids: gridsData.result,
      pagination: gridsData.pagination,
    }
  );
};
