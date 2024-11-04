import React from "react";
import { Link as SDSLink } from "@czi-sds/components";
import { Props } from "@/app/components/Table/components/CellComponent/components/Link/types";
import { LINK_PROPS } from "@/app/components/Table/components/CellComponent/components/Link/constants";
import { RowData } from "@tanstack/react-table";

export const Link = <TData extends RowData>({
  getValue,
}: Props<TData>): JSX.Element => {
  const tValue = getValue();
  return <SDSLink {...LINK_PROPS} {...tValue} />;
};
