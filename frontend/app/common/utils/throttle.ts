/**
 * @returns a version of `func` that limits its execution to once every `intervalMs`.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function throttle<T extends (...args: any[]) => void>(
  func: T,
  intervalMs: number
): (...args: Parameters<T>) => void {
  let lastExecuteTimeMs: number | undefined;
  let currentTimeoutId: ReturnType<typeof setTimeout> | undefined;

  return function (...args: Parameters<T>) {
    const now = Date.now();
    clearTimeout(currentTimeoutId);
    if (lastExecuteTimeMs === undefined || now - lastExecuteTimeMs >= intervalMs) {
      lastExecuteTimeMs = now;
      func(...args);
    } else {
      currentTimeoutId = setTimeout(
        () => {
          lastExecuteTimeMs = now;
          func(...args);
        },
        intervalMs - (now - lastExecuteTimeMs)
      );
    }
  };
}
