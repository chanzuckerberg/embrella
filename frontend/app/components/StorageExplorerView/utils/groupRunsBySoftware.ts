import { formatBytes } from '@app/common/utils/format';

import { StorageRunRow, StorageSessionData, StorageSoftwareGroup, StorageStatus } from '../types';

/**
 * One status for a parent from its children's.
 *
 * Mirrors `rollup_status` in processes/services/decisions.py: unanimous
 * collapses to the shared value, disagreement is 'mixed'. Keep the two in step
 * — the session tier's status comes from the server and the software tier's
 * from here, and they sit in adjacent rows.
 */
function rollupStatus(runs: StorageRunRow[]): StorageStatus {
  const distinct = new Set(runs.map((run) => run.status));
  if (distinct.size === 0) return 'unset';
  if (distinct.size === 1) return [...distinct][0];
  return 'mixed';
}

/**
 * Build the software tier from a session's flat `runs`.
 *
 * The API models only the session and the leaf, so this level exists only here.
 * That is safe because every figure it shows is associative: sizes and counts
 * sum, `lastModified` is a max. The rollup is exact, not an approximation — a
 * software group's total always equals the sum of its runs', and the session
 * total always equals the sum of its groups'.
 *
 * Sizes are re-formatted client-side rather than summing the server's display
 * strings, which is why formatBytes has to match the server's format_bytes.
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
        // Session-root leaves carry files sitting directly under the session
        // directory; they are not runs, and the API's runCount excludes them too.
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
