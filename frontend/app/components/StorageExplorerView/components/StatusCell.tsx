import { Tag } from '@czi-sds/components';
import styled from '@emotion/styled';

import { gray100 } from '@app/common/theme';

import { statusLabel } from '../constants/statusLabels';
import { useStorageDecisions } from '../context/StorageDecisionContext';
import { StorageStatus } from '../types';

/**
 * SDS's `neutral` intent fills with gray-200 (#dfdfdf), which is heavy for the
 * status most rows are in — nearly the whole table is undecided, so a mid grey
 * across all of it reads as noise and leaves nothing for the decided rows to
 * stand out against. One step lighter on the same ramp; SDS's gray-700 label
 * still gives 12:1 contrast.
 */
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

interface StatusCellProps {
  status: StorageStatus;
  /** Names the thing being decided, e.g. "session 26mar02a". */
  label: string;
  /**
   * Directories this row's decision covers. One entry for a run or a software
   * folder; one per software folder for a session.
   */
  pathPrefixes: string[];
  totalSizeDisplay: string;
  directoryCount: number;
  /** The row's own directory, where it has exactly one. Enables inherited detection. */
  pathPrefix?: string;
  decidedAtPrefix?: string | null;
}

/**
 * A row's preservation status, at any tier, and the control that sets it.
 *
 * "Delete" is a recorded judgement that a directory looks reclaimable. Nothing
 * in this view deletes, moves or modifies a file.
 *
 * A tag rather than text because it is also the affordance: SDS Tag is
 * clickable and has a hover state, so the thing showing the current value is
 * the thing you click to change it. Outside the decision provider it degrades
 * to a plain label rather than throwing, so a tier can be rendered on its own.
 *
 * Inheritance is not marked here — the menu says "Inherited from the tier
 * above" when it applies, which is the point at which it matters.
 */
export const StatusCell = ({
  status,
  label,
  pathPrefixes,
  totalSizeDisplay,
  directoryCount,
  pathPrefix,
  decidedAtPrefix,
}: StatusCellProps): React.JSX.Element => {
  const decisions = useStorageDecisions();
  const inheritedFrom = decidedAtPrefix && pathPrefix && decidedAtPrefix !== pathPrefix ? decidedAtPrefix : null;
  const Component = status === 'unset' ? QuietTag : Tag;

  return (
    <Component
      label={statusLabel(status)}
      color={STATUS_COLOR[status] ?? 'neutral'}
      sdsType="secondary"
      sdsStyle="rounded"
      hover={Boolean(decisions)}
      onClick={
        decisions
          ? (event: React.MouseEvent<HTMLElement>) => {
              // Rows toggle expansion on click; without this the menu opens and
              // the row collapses underneath it.
              event.stopPropagation();
              decisions.openMenu(event.currentTarget, {
                label,
                pathPrefixes,
                status,
                totalSizeDisplay,
                directoryCount,
                inheritedFrom,
              });
            }
          : undefined
      }
    />
  );
};
