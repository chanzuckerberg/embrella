import { NestedSubRowTable } from '@app/common/components/NestedSubRowTable/NestedSubRowTable';

import { STORAGE_RUN_COLUMN_DEFS } from '../constants/runColumns';
import { StorageRunRow } from '../types';

interface SoftwareRunsSubRowProps {
  runs: StorageRunRow[];
}

/**
 * Third and last tier: the runs under one software folder.
 */
export const SoftwareRunsSubRow = ({ runs }: SoftwareRunsSubRowProps): React.JSX.Element => (
  <NestedSubRowTable<StorageRunRow>
    data={runs}
    columnDefs={STORAGE_RUN_COLUMN_DEFS}
    // Already namespaced as "storagerun-<pk>" by the API.
    getRowId={(run) => run.id}
    emptyMessage="No runs under this software"
    minWidth={700}
  />
);
