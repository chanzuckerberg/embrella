/**
 * Calculate the next run name from a list of run numbers.
 * Run numbers are bare digits without 'run' prefix (e.g., ['001', '002']).
 * Returns the next run name with prefix (e.g., 'run003').
 */
export function calculateNextRunName(runNumbers: string[]): string {
  let nextRunNum = 1;
  if (runNumbers.length > 0) {
    const maxNum = Math.max(...runNumbers.map((n: string) => parseInt(n, 10) || 0));
    nextRunNum = maxNum + 1;
  }
  return `run${String(nextRunNum).padStart(3, '0')}`;
}
