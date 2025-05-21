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
    const execute = () => {
      lastExecuteTimeMs = now;
      func(...args);
    };

    if (lastExecuteTimeMs === undefined || now - lastExecuteTimeMs >= intervalMs) {
      execute();
    } else {
      clearTimeout(currentTimeoutId);
      currentTimeoutId = setTimeout(
        () => {
          currentTimeoutId = undefined;
          execute();
        },
        intervalMs - (now - lastExecuteTimeMs)
      );
    }
  };
}
