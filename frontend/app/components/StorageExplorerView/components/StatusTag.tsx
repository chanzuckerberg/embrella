import { Tooltip } from '@mui/material';
import { Tag } from '@czi-sds/components';
import styled from '@emotion/styled';

import { gray100 } from '@app/common/theme';

import { StorageStatus } from '../types';
import { statusLabel } from '../constants/statusLabels';

const QuietTag = styled(Tag)`
  background-color: ${gray100};
`;

const STATUS_COLOR: Record<StorageStatus, 'info' | 'negative' | 'neutral' | 'notice' | 'positive'> = {
  unset: 'neutral',
  preserve: 'positive',
  delete: 'negative',
  review: 'notice',
  mixed: 'info',
};

interface StatusTagProps {
  status: StorageStatus;
  /** Path the decision was recorded against; shorter than the row's own means inherited. */
  decidedAtPrefix?: string | null;
  /** The row's own path, to compare against `decidedAtPrefix`. */
  pathPrefix?: string;
  /**
   * Opens the set-status menu. Unused until decisions ship — this is the hook
   * that turns the tag from a label into the control, which is why status is a
   * tag rather than plain text.
   */
  onClick?: () => void;
}

/**
 * A row's preservation status, at any tier.
 *
 * "Delete" is a recorded judgement that a directory looks reclaimable. Nothing
 * in this view deletes, moves or modifies a file.
 */
export const StatusTag = ({ status, decidedAtPrefix, pathPrefix, onClick }: StatusTagProps): React.JSX.Element => {
  const inherited = Boolean(decidedAtPrefix && pathPrefix && decidedAtPrefix !== pathPrefix);
  const Component = status === 'unset' ? QuietTag : Tag;

  const tag = (
    <Component
      label={statusLabel(status)}
      color={STATUS_COLOR[status] ?? 'neutral'}
      sdsType="secondary"
      sdsStyle="rounded"
      hover={Boolean(onClick)}
      onClick={onClick}
    />
  );

  if (!inherited) return tag;

  // Without this there is no way to tell why a run reads "Delete", or which row
  // to change to undo it.
  return (
    <Tooltip title={`Inherited from ${decidedAtPrefix}`}>
      <span>{tag}</span>
    </Tooltip>
  );
};
