import React from "react";

import { useConnect } from "@app/components/TomogramsView/components/TomogramTable/connect";
import { EntityTable } from "@/app/components/EntityTable/EntityTable";
import { TOMOGRAM_COLUMN_DEFS } from "./columns";

// TODO: Remove this component and put it directly in parent view
export const TomogramTable = (): React.JSX.Element => {
  const { tomogramList } = useConnect();
  return <EntityTable
    entityList={tomogramList}
    entityApiResponseField="tomograms"
    columnDefs={TOMOGRAM_COLUMN_DEFS}
  ></EntityTable>
}
