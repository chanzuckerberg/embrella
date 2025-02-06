import { Link } from "@czi-sds/components";

import { EntityLinkField } from "@app/common/types/entity";
import { CellContext } from "@tanstack/react-table";
import { EntityDataTypes } from "@app/common/types/tableState";
import {
  AccessorReturnType,
  LinkCellProps,
} from "@app/common/components/EntityTable/types";

const DEFAULT_LINK_PROPS = {
  sdsStyle: "default",
  target: "_blank",
};

export const getLinkPropsFromLinkField = (
  linkField: EntityLinkField,
): LinkCellProps => ({
  children: linkField.name,
  href: linkField.url,
});


export const getLinkPropsFromLinkFieldList = (
  linkFields?: EntityLinkField[], // Ensure it's optional
): LinkCellProps[] => (Array.isArray(linkFields) ? linkFields.map(getLinkPropsFromLinkField) : []);

export const getLinkCellFromCellContext = (
  props: CellContext<EntityDataTypes, AccessorReturnType>,
): React.JSX.Element => {
  const linkProps = (
    props as CellContext<EntityDataTypes, LinkCellProps>
  ).getValue();

  return <Link {...DEFAULT_LINK_PROPS} {...linkProps} />;
};

export const getLinkCellListFromCellContext = (
  props: CellContext<EntityDataTypes, AccessorReturnType>,
): React.JSX.Element => {
  const linkCellPropsList = (
    props as CellContext<EntityDataTypes, LinkCellProps[]>
  ).getValue();

  if (!Array.isArray(linkCellPropsList)) {
    throw new Error("Link cell props must be an array");
  }

  return (
    <>
      {linkCellPropsList.map((linkCellProps, i) => (
        <div key={i}>
          <Link {...DEFAULT_LINK_PROPS} {...linkCellProps} />
        </div>
      ))}
    </>
  );
};
