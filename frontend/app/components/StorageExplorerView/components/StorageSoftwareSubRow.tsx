import { useMemo } from 'react';

import { NestedSubRowTable } from '@app/common/components/NestedSubRowTable/NestedSubRowTable';

import { STORAGE_SOFTWARE_COLUMN_DEFS } from '../constants/softwareColumns';
import { StorageSessionData, StorageSoftwareGroup } from '../types';
import { groupRunsBySoftware } from '../utils/groupRunsBySoftware';
import { SoftwareRunsSubRow } from './SoftwareRunsSubRow';

interface StorageSoftwareSubRowProps {
  data: StorageSessionData;
}

/**
 * Second tier: one row per on-disk software folder, each expanding to its runs.
 *
 * A session genuinely appears under several software folders — the same session
 * can hold aretomo3, denoise and membraneseg output — which is why software
 * nests under session rather than the reverse.
 */
export const StorageSoftwareSubRow = ({ data }: StorageSoftwareSubRowProps): React.JSX.Element => {
  const groups = useMemo(() => groupRunsBySoftware(data), [data]);

  return (
    <NestedSubRowTable<StorageSoftwareGroup>
      data={groups}
      columnDefs={STORAGE_SOFTWARE_COLUMN_DEFS}
      getRowId={(group) => group.id}
      getChildren={(group) => group.runs}
      renderChild={(group) => <SoftwareRunsSubRow runs={group.runs} />}
      emptyMessage="No processing output for this session"
      childLabel="runs"
      minWidth={760}
    />
  );
};
