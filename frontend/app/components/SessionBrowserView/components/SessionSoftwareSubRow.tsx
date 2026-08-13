import React, { useMemo } from 'react';

import { NestedSubRowTable } from '@app/common/components/NestedSubRowTable/NestedSubRowTable';

import { SESSION_SOFTWARE_COLUMN_DEFS } from '../constants/softwareColumns';
import { SessionOverviewData, SessionSoftwareGroup } from '../types';
import { groupRunsBySoftware } from '../utils/groupRunsBySoftware';
import { SoftwareRunsSubRow } from './SoftwareRunsSubRow';

interface SessionSoftwareSubRowProps {
  data: SessionOverviewData;
}

/**
 * Middle tier of the session browser: one row per processing-software display
 * name, each expanding to that software's runs.
 *
 * Note this shows every software on the session even when a
 * `processingSoftware` filter is active — the backend filters which *sessions*
 * match, not which runs come back, so the expanded view stays a complete
 * picture of the session.
 */
export const SessionSoftwareSubRow = ({ data }: SessionSoftwareSubRowProps) => {
  const groups = useMemo(() => groupRunsBySoftware(data), [data]);

  return (
    <NestedSubRowTable<SessionSoftwareGroup>
      data={groups}
      columnDefs={SESSION_SOFTWARE_COLUMN_DEFS}
      getRowId={(group) => group.id}
      getChildren={(group) => group.runs}
      renderChild={(group) => <SoftwareRunsSubRow runs={group.runs} />}
      emptyMessage="No processing runs for this session"
      childLabel="runs"
    />
  );
};
