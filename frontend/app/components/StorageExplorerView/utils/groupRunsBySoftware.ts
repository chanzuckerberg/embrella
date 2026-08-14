import { formatBytes } from '@app/common/utils/format';

import { StorageRunRow, StorageSessionData, StorageSoftwareGroup, StorageStatus } from '../types';

/**
 * One status for a parent from its children's.
 */
function rollupStatus(runs: StorageRunRow[]): StorageStatus {
  const distinct = new Set(runs.map((run) => run.status));
  if (distinct.size === 0) return 'unset';
  if (distinct.size === 1) return [...distinct][0];
  return 'mixed';
}

/**
 * Build the software tier from a session's flat `runs`.
 */
export function groupRunsBySoftware(data: StorageSessionData): StorageSoftwareGroup[] {
  const groups = new Map<string, StorageRunRow[]>();

  for (const run of data.runs) {
    const existing = groups.get(run.software);
    if (existing) {
      existing.push(run);
    } else {
      groups.set(run.software, [run]);
    }
  }

  return Array.from(groups.entries())
    .map(([software, runs]) => {
      const totalSizeBytes = runs.reduce((sum, run) => sum + run.totalSizeBytes, 0);
      const modified = runs.map((run) => run.lastModified).filter((value): value is string => Boolean(value));

      return {
        id: `storagesoftware-${data.sessionName}-${software}`,
        software,
        pathPrefix: runs[0].softwarePathPrefix,
        runCount: runs.filter((run) => run.run.name !== '(session root)').length,
        directoryCount: runs.reduce((sum, run) => sum + run.directoryCount, 0),
        fileCount: runs.reduce((sum, run) => sum + run.fileCount, 0),
        totalSizeBytes,
        totalSizeDisplay: formatBytes(totalSizeBytes),
        lastModified: modified.length > 0 ? modified.reduce((a, b) => (a > b ? a : b)) : null,
        status: rollupStatus(runs),
        runs: [...runs].sort((a, b) => a.run.name.localeCompare(b.run.name, undefined, { numeric: true })),
      };
    })
    .sort((a, b) => b.totalSizeBytes - a.totalSizeBytes);
}
