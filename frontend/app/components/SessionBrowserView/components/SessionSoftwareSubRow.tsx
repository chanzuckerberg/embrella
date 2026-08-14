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
 * Session browser's software tier
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
