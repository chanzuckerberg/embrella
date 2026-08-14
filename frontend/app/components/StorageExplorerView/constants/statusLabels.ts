import { STATUS_LABELS } from '@app/components/DirectoryExplorerView/types';

import { StorageStatus } from '../types';

/**
 * Status text, reusing the All Paths tab's labels.
 */
export function statusLabel(status: StorageStatus): string {
  return status === 'mixed' ? 'Mixed' : (STATUS_LABELS[status] ?? status);
}
