import { Link } from "@czi-sds/components";

import { EntityLinkField } from "@app/common/types/entity";
import { CellContext } from "@tanstack/react-table";
import { EntityDataTypes } from "@/app/common/types/tableState";
import { AccessorReturnType } from "@/app/common/components/EntityTable/types";

const DEFAULT_LINK_PROPS = {
  sdsStyle: "default",
  target: "_blank",
};

export interface LinkCellProps {
  children: string;
  href: string;
}

export const getLinkPropsFromLinkField = (linkField: EntityLinkField) => ({
  children: linkField.name,
  href: linkField.url,
});

export const getLinkCellFromCellContext = (
  props: CellContext<EntityDataTypes, AccessorReturnType>,
): React.JSX.Element => {
  return <LinkCell {...props} />;
};

export const LinkCell = (
  props: CellContext<EntityDataTypes, AccessorReturnType>,
): React.JSX.Element => {
  // Cast CellContext to LinkCellProps since this function is only used for cells that display links
  const linkCellProps = (
    props as CellContext<EntityDataTypes, LinkCellProps>
  ).getValue();

  return <Link {...DEFAULT_LINK_PROPS} {...linkCellProps} />;
};
