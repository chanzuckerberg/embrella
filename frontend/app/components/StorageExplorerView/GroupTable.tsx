import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { API } from '@app/common/constants/api';

import { StorageSoftwareSubRow } from './components/StorageSoftwareSubRow';
import { STORAGE_COLUMN_DEFS } from './constants/columns';
import { StorageSessionData } from './types';

interface GroupTableProps {
  /** Empty means "let the backend pick its configured default". */
  cluster: string;
}

/**
 * The storage session tier.
 */
export const GroupTable = ({ cluster }: GroupTableProps): React.JSX.Element => (
  <EntityTable
    entityApi={
      (cluster ? `${API.STORAGE_SESSIONS}?cluster=${encodeURIComponent(cluster)}` : API.STORAGE_SESSIONS) as API
    }
    entityApiResponseField="storageSession"
    columnDefs={STORAGE_COLUMN_DEFS}
    getSubRows={(row: StorageSessionData) => row.runs as unknown[]}
    renderSubRow={(row) => <StorageSoftwareSubRow data={row.original as StorageSessionData} />}
  />
);
