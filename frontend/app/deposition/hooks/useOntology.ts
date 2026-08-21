import { useQuery } from '@tanstack/react-query';

import { searchOntology, validateOntologyId, type OntologyTerm } from '../services/ols';

const olsKeys = {
  search: (ontology: string, term: string, childrenOf?: string) =>
    ['ols', 'search', ontology, term, childrenOf ?? ''] as const,
  term: (ontology: string, id: string) => ['ols', 'term', ontology, id] as const,
};

const STALE = 5 * 60 * 1000;

export function useOntologySearch(term: string, ontology: string, enabled = true, childrenOf?: string) {
  return useQuery<OntologyTerm[]>({
    queryKey: olsKeys.search(ontology, term.trim(), childrenOf),
    queryFn: () => searchOntology(term, ontology, childrenOf),
    enabled: enabled && term.trim().length >= 2,
    staleTime: STALE,
  });
}

/** Resolve an OBO id for id↔label validation. */
export function useOntologyTerm(id: string, ontology: string, enabled = true) {
  return useQuery<OntologyTerm | null>({
    queryKey: olsKeys.term(ontology, id.trim()),
    queryFn: () => validateOntologyId(id, ontology),
    enabled: enabled && id.trim().length > 0,
    staleTime: STALE,
  });
}
