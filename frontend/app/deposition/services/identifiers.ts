// ORCID + DOI validation via their public APIs

export const ORCID_RE = /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/;
export const DOI_RE = /^(doi:)?10\.\d{4,9}\/[-._;()/:a-zA-Z0-9]+$/;
export const EMPIAR_RE = /^EMPIAR-\d{5}$/;
export const EMDB_RE = /^EMD-\d{4,5}$/;
export const PDB_RE = /^PDB-[0-9a-zA-Z]{4,8}$/;
export const RELATED_DB_RE = /^(EMPIAR-\d{5}|EMD-\d{4,5}|PDB-[0-9a-zA-Z]{4,8})$/;

export type IdentifierKind = 'orcid' | 'doi' | 'related_db';

export interface ResolvedIdentifier {
  label: string;
}

export function orcidChecksumOk(orcid: string): boolean {
  const digits = orcid.replace(/-/g, '');
  if (digits.length !== 16) return false;
  let total = 0;
  for (let i = 0; i < 15; i += 1) total = (total + Number(digits[i])) * 2;
  const remainder = total % 11;
  const check = (12 - remainder) % 11;
  const expected = check === 10 ? 'X' : String(check);
  return digits[15].toUpperCase() === expected;
}

export async function validateOrcid(orcid: string): Promise<ResolvedIdentifier | null> {
  const id = orcid.trim();
  if (!ORCID_RE.test(id) || !orcidChecksumOk(id)) return null;
  const res = await fetch(`https://pub.orcid.org/v3.0/${id}/person`, {
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`ORCID lookup failed: ${res.status}`);
  const data = await res.json();
  const name = data?.name;
  const label =
    name?.['credit-name']?.value ||
    [name?.['given-names']?.value, name?.['family-name']?.value].filter(Boolean).join(' ') ||
    'valid ORCID';
  return { label };
}

// Strip a resolver-URL prefix
export function normalizeDoi(value: string): string {
  return value.replace(/^\s*(?:https?:\/\/)?(?:www\.|dx\.)?doi\.org\//i, '');
}

export async function validateDoi(doi: string): Promise<ResolvedIdentifier | null> {
  const normalized = normalizeDoi(doi).trim();
  const id = normalized.replace(/^doi:/i, '');
  if (!DOI_RE.test(normalized)) return null;

  const res = await fetch(`https://api.crossref.org/works/${id}`);
  if (res.ok) {
    const data = await res.json();
    const title: string | undefined = data?.message?.title?.[0];
    return { label: title || 'valid DOI' };
  }

  const resolver = await fetch(`https://doi.org/${id}`, { method: 'HEAD', redirect: 'manual' });
  if (resolver.type === 'opaqueredirect' || (resolver.status > 0 && resolver.status < 400)) {
    return { label: 'valid DOI' };
  }
  if (resolver.status === 404) return null;
  throw new Error(`DOI resolver failed: ${resolver.status}`);
}

async function existenceCheck(url: string, label: string): Promise<ResolvedIdentifier | null> {
  const res = await fetch(url);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Related-DB lookup failed: ${res.status}`);
  return { label };
}

export async function validateRelatedDb(value: string): Promise<ResolvedIdentifier | null> {
  const v = value.trim();
  if (EMPIAR_RE.test(v)) return existenceCheck(`https://www.ebi.ac.uk/empiar/api/entry/${v}/`, 'EMPIAR entry');
  if (EMDB_RE.test(v)) return existenceCheck(`https://www.ebi.ac.uk/emdb/api/entry/${v}`, 'EMDB entry');
  if (PDB_RE.test(v)) {
    return existenceCheck(`https://data.rcsb.org/rest/v1/core/entry/${v.replace(/^PDB-/, '')}`, 'PDB entry');
  }
  return null;
}

export function validateIdentifier(kind: IdentifierKind, value: string): Promise<ResolvedIdentifier | null> {
  if (kind === 'orcid') return validateOrcid(value);
  if (kind === 'doi') return validateDoi(value);
  return validateRelatedDb(value);
}
