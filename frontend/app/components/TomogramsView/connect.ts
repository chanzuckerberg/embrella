import { SEARCH_PARAM_NAME } from "@/app/common/types/search";
import { useFetchTomograms } from "./hooks/useFetchTomograms/useFetchTomograms";

export const useConnect = () => {
  const tomogramList = useFetchTomograms({ [SEARCH_PARAM_NAME.QUERY]: [] });
  return { tomogramList };
};
