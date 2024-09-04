import React, { Fragment } from "react";
import { Props } from "@/components/Table/components/CellComponent/components/Links/types";
import { Link as SDSLink } from "@czi-sds/components";
import { LINK_PROPS } from "@/components/Table/components/CellComponent/components/Link/constants";
import { RowData } from "@tanstack/react-table";

export const Links = <TData extends RowData>({
  getValue,
}: Props<TData>): JSX.Element => {
  const tValues = getValue();
  return (
    <Fragment>
      {tValues.map((tValue, i) => (
        <div key={i}>
          <SDSLink {...LINK_PROPS} {...tValue} />
        </div>
      ))}
    </Fragment>
  );
};
