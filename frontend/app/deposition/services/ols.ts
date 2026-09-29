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

export async function searchOntology(term: string, ontology: string, childrenOf?: string): Promise<OntologyTerm[]> {
  const q = term.trim();
  if (!q) return Promise.resolve([]);
  const params: Record<string, string> = { q, ontology: ontology.toLowerCase() };
  // Restrict to subtree rooted at this IRI
  if (childrenOf) params.childrenOf = childrenOf;
  if (ontology.toLowerCase() !== 'ncbitaxon') return olsQuery('select', params);
  const [suggestions, exact] = await Promise.all([
    olsQuery('select', { ...params, rows: '50' }),
    olsQuery('search', { ...params, exact: 'true', queryFields: 'label,synonym', rows: '50' }),
  ]);
  const terms = [...new Map([...exact, ...suggestions].map((term) => [term.id, term])).values()];
  const query = q.toLowerCase();
  const rank = (term: OntologyTerm) => {
    if (term.label.toLowerCase() === query) return 0;
    if (term.synonyms.some((synonym) => synonym.toLowerCase() === query)) return 1;
    return term.label.toLowerCase().startsWith(query) ? 2 : 3;
  };
  return terms.sort((a, b) => rank(a) - rank(b) || a.label.length - b.label.length).slice(0, 50);
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
  return results.find((t) => t.id.toLowerCase() === q.toLowerCase()) ?? null;
}
