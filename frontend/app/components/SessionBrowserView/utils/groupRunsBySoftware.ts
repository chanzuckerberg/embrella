import { SessionOverviewData, SessionRunRow, SessionSoftwareGroup } from '../types';

/**
 * Build the software tier of the session browser from a session's flat `runs`.
 */
export function groupRunsBySoftware(data: SessionOverviewData): SessionSoftwareGroup[] {
  const groups = new Map<string, SessionRunRow[]>();

  for (const run of data.runs) {
    const existing = groups.get(run.planLabel);
    if (existing) {
      existing.push(run);
    } else {
      groups.set(run.planLabel, [run]);
    }
  }

  return Array.from(groups.entries())
    .map(([planLabel, runs]) => ({
      id: `software-${data.session.id}-${planLabel}`,
      planLabel,
      planNames: Array.from(new Set(runs.map((run) => run.planName))).sort(),
      runCount: runs.length,
      latestRunAt: runs[0]?.createdAt ?? null,
      runs,
    }))
    .sort((a, b) => a.planLabel.localeCompare(b.planLabel));
}
