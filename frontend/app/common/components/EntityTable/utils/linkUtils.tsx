import { Link } from '@czi-sds/components';

import { EntityLinkField } from '@app/common/types/entity';
import { CellContext } from '@tanstack/react-table';
import { EntityDataTypes } from '@app/common/types/tableState';
import { AccessorReturnType, LinkCellProps } from '@app/common/components/EntityTable/types';

const DEFAULT_LINK_PROPS = {
  sdsStyle: 'default',
  target: '_blank',
};

// The tomogram, annotation and review columns render `<field>.name` as plain text instead of
// using these helpers: their urls point at Django admin, which does not work for non-staff users.
// TODO: swap them back to these helpers once a real browser view exists for those entities.
export const getLinkPropsFromLinkField = (linkField: EntityLinkField): LinkCellProps => ({
  children: linkField.name,
  href: linkField.url,
});

export const getLinkPropsFromLinkFieldList = (
  linkFields?: EntityLinkField[] // Ensure it's optional
): LinkCellProps[] => (Array.isArray(linkFields) ? linkFields.map(getLinkPropsFromLinkField) : []);

export const getLinkCellFromCellContext = (
  props: CellContext<EntityDataTypes, AccessorReturnType>
): React.JSX.Element => {
  const linkProps = (props as CellContext<EntityDataTypes, LinkCellProps>).getValue();

  return <Link {...DEFAULT_LINK_PROPS} {...linkProps} />;
};

export const getLinkCellListFromCellContext = (
  props: CellContext<EntityDataTypes, AccessorReturnType>
): React.JSX.Element => {
  const linkCellPropsList = (props as CellContext<EntityDataTypes, LinkCellProps[]>).getValue();

  if (!Array.isArray(linkCellPropsList)) {
    throw new Error('Link cell props must be an array');
  }

  return (
    <div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
      {linkCellPropsList.map((linkCellProps, i) => (
        <span key={i}>
          <Link {...DEFAULT_LINK_PROPS} {...linkCellProps} />
          {i < linkCellPropsList.length - 1 && ', '}
        </span>
      ))}
    </div>
  );
};

export interface CellLinkProps {
  linkField: EntityLinkField;
}

export const CellLink = ({ linkField }: CellLinkProps) => {
  return (
    <Link href={linkField.url} sdsStyle="default" target="_blank">
      {linkField.name}
    </Link>
  );
};
