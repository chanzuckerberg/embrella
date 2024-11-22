import React from "react";

import { EntityTable } from "@/app/components/EntityTable/EntityTable";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";
import { API } from "@/app/common/constants/api";

// TODO: Remove this component and put it directly in parent view
export const TomogramTable = (): React.JSX.Element => {
  return (
    <EntityTable
      entityApi={API.TOMOGRAMS_V1}
      entityApiResponseField="tomograms"
      columnDefs={TOMOGRAM_COLUMN_DEFS}
    ></EntityTable>
  );
};
