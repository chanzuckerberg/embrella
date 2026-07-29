import { useQuery } from '@tanstack/react-query';

import { validateIdentifier, type IdentifierKind, type ResolvedIdentifier } from '../services/identifiers';

const STALE = 5 * 60 * 1000;

export function useIdentifierLookup(kind: IdentifierKind, value: string, enabled: boolean) {
  return useQuery<ResolvedIdentifier | null>({
    queryKey: ['identifier', kind, value.trim()],
    queryFn: () => validateIdentifier(kind, value),
    enabled: enabled && value.trim().length > 0,
    staleTime: STALE,
  });
}
