import { useContext } from "react";

import { SEARCH_PARAM_NAME } from "@app/common/types/search";
// import { useFetchTomograms } from "@app/components/TomogramsView/hooks/useFetchTomograms/useFetchTomograms";
import { TableStateContext } from "@app/common/components/TableStateProvider/TableStateProvider";
import { useFetchTableData } from "@/app/common/hooks/useFetchTableData/useFetchTableData";
import { API } from "@/app/common/constants/api";
import { TomogramData } from "@/app/common/types/tomogram";

const TOMOGRAM_RESPONSE_FIELD = "tomograms" as const;

export const useConnect = () => {
  const state = useContext(TableStateContext);

  const tomogramList = useFetchTableData<
    TomogramData,
    typeof TOMOGRAM_RESPONSE_FIELD
  >(
    API.TOMOGRAMS_V1,
    {
      [SEARCH_PARAM_NAME.QUERY]: [],
    },
    TOMOGRAM_RESPONSE_FIELD
  );
  return { tomogramList };
};
