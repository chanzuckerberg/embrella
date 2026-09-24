const OLS_BASE = 'https://www.ebi.ac.uk/ols4/api';

// GO: scope Cell component / annotation-object suggestions to Cellular Component.
// eslint-disable-next-line sonarjs/no-clear-text-protocols
export const GO_CELLULAR_COMPONENT_IRI = 'http://purl.obolibrary.org/obo/GO_0005575';

export interface OntologyTerm {
  id: string; // OBO id, e.g. "UBERON:0000955"
  label: string;
  synonyms: string[];
  iri?: string;
}

interface OlsDoc {
  iri?: string;
  label?: string;
  obo_id?: string;
  synonym?: string[];
}

function toTerm(doc: OlsDoc): OntologyTerm | null {
  if (!doc.obo_id || !doc.label) return null;
  return { id: doc.obo_id, label: doc.label, synonyms: doc.synonym ?? [], iri: doc.iri };
}

async function olsQuery(endpoint: 'search' | 'select', params: Record<string, string>): Promise<OntologyTerm[]> {
  const qs = new URLSearchParams({ rows: '10', fieldList: 'obo_id,label,synonym,iri', ...params }).toString();
  const res = await fetch(`${OLS_BASE}/${endpoint}?${qs}`);
  if (!res.ok) throw new Error(`OLS ${endpoint} failed: ${res.status}`);
  const data = await res.json();
  const docs: OlsDoc[] = data?.response?.docs ?? [];
  return docs.map(toTerm).filter((t): t is OntologyTerm => t !== null);
}

export function searchOntology(term: string, ontology: string, childrenOf?: string): Promise<OntologyTerm[]> {
  const q = term.trim();
  if (!q) return Promise.resolve([]);
  const params: Record<string, string> = { q, ontology: ontology.toLowerCase() };
  // Restrict to subtree rooted at this IRI
  if (childrenOf) params.childrenOf = childrenOf;
  return olsQuery('select', params);
}

/** Validate an OBO id */
export async function validateOntologyId(id: string, ontology: string): Promise<OntologyTerm | null> {
  const q = id.trim();
  if (!q) return null;
  const results = await olsQuery('search', {
    q,
    ontology: ontology.toLowerCase(),
    exact: 'true',
    queryFields: 'obo_id',
  });
  return results.find((t) => t.id.toLowerCase() === q.toLowerCase()) ?? results[0] ?? null;
}
