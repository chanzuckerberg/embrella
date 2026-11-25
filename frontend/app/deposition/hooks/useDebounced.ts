import { useEffect, useState } from 'react';

// TODO: duplicate of @app/common/hooks/useDebounced. Point deposition imports there and delete this (.planning/shared-debounce-hook.md).

export function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}
