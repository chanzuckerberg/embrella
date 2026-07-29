import {
  orcidChecksumOk,
  validateDoi,
  validateOrcid,
  validateRelatedDb,
  DOI_RE,
  ORCID_RE,
  RELATED_DB_RE,
} from './identifiers';

function mockFetch(body: unknown, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }) as unknown as typeof fetch;
}

afterEach(() => jest.restoreAllMocks());

describe('format regexes', () => {
  it('ORCID_RE accepts a well-formed id and an X check digit', () => {
    expect(ORCID_RE.test('0000-0002-1825-0097')).toBe(true);
    expect(ORCID_RE.test('0000-0002-1694-233X')).toBe(true);
  });
  it('ORCID_RE rejects malformed ids', () => {
    expect(ORCID_RE.test('0000-0002-1825-009')).toBe(false);
    expect(ORCID_RE.test('junk')).toBe(false);
  });
  it('DOI_RE accepts a bare and doi:-prefixed DOI', () => {
    expect(DOI_RE.test('10.1038/nature12373')).toBe(true);
    expect(DOI_RE.test('doi:10.1038/nature12373')).toBe(true);
  });
  it('DOI_RE rejects a non-DOI string', () => {
    expect(DOI_RE.test('nature12373')).toBe(false);
  });
});

describe('orcidChecksumOk', () => {
  it('accepts a valid checksum and rejects a tampered one', () => {
    expect(orcidChecksumOk('0000-0002-1825-0097')).toBe(true);
    expect(orcidChecksumOk('0000-0002-1825-0098')).toBe(false);
  });
});

describe('validateOrcid', () => {
  it('resolves to the record owner name', async () => {
    mockFetch({ name: { 'given-names': { value: 'Josiah' }, 'family-name': { value: 'Carberry' } } });
    expect(await validateOrcid('0000-0002-1825-0097')).toEqual({ label: 'Josiah Carberry' });
  });
  it('returns null on 404 without throwing', async () => {
    mockFetch({}, 404);
    expect(await validateOrcid('0000-0002-1825-0097')).toBeNull();
  });
  it('returns null for a checksum-invalid id without hitting the network', async () => {
    mockFetch({});
    expect(await validateOrcid('0000-0002-1825-0098')).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });
  it('throws on a server error', async () => {
    mockFetch({}, 500);
    await expect(validateOrcid('0000-0002-1825-0097')).rejects.toThrow(/ORCID lookup failed: 500/);
  });
});

describe('validateDoi', () => {
  it('resolves to the work title and strips a doi: prefix', async () => {
    mockFetch({ message: { title: ['Nanometre-scale thermometry in a living cell'] } });
    expect(await validateDoi('doi:10.1038/nature12373')).toEqual({
      label: 'Nanometre-scale thermometry in a living cell',
    });
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain('10.1038');
    expect(url).not.toContain('doi:');
  });
  it('returns null when both CrossRef and doi.org miss (404)', async () => {
    mockFetch({}, 404);
    expect(await validateDoi('10.9999/nope')).toBeNull();
  });

  it('falls back to doi.org when CrossRef misses (DataCite DOI resolves via redirect)', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) }) // CrossRef miss
      .mockResolvedValueOnce({ type: 'opaqueredirect', status: 0 }) as unknown as typeof fetch; // doi.org 3xx hit
    expect(await validateDoi('10.5281/zenodo.10047439')).toEqual({ label: 'valid DOI' });
    const calls = (global.fetch as jest.Mock).mock.calls;
    expect(calls[0][0]).toContain('api.crossref.org');
    expect(calls[1][0]).toContain('doi.org');
    expect(calls[1][1]).toMatchObject({ method: 'HEAD', redirect: 'manual' });
  });

  it('falls back to doi.org on a CrossRef 5xx (rides out the hiccup, like the portal)', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({}) }) // CrossRef down
      .mockResolvedValueOnce({ type: 'opaqueredirect', status: 0 }) as unknown as typeof fetch; // doi.org hit
    expect(await validateDoi('10.1038/nature12373')).toEqual({ label: 'valid DOI' });
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('doi.org');
  });
  it('returns null for a malformed DOI without hitting the network', async () => {
    mockFetch({});
    expect(await validateDoi('not-a-doi')).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe('validateRelatedDb', () => {
  it('RELATED_DB_RE accepts EMPIAR / EMD / PDB and rejects junk', () => {
    expect(RELATED_DB_RE.test('EMPIAR-10943')).toBe(true);
    expect(RELATED_DB_RE.test('EMD-11657')).toBe(true);
    expect(RELATED_DB_RE.test('PDB-4hhb')).toBe(true);
    expect(RELATED_DB_RE.test('10.1038/nature12373')).toBe(false);
  });

  it('resolves an existing EMPIAR entry (full id in the URL)', async () => {
    mockFetch({}, 200);
    expect(await validateRelatedDb('EMPIAR-10943')).toEqual({ label: 'EMPIAR entry' });
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/empiar/api/entry/EMPIAR-10943/');
  });

  it('strips the PDB- prefix before hitting RCSB', async () => {
    mockFetch({}, 200);
    expect(await validateRelatedDb('PDB-4hhb')).toEqual({ label: 'PDB entry' });
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain('/core/entry/4hhb');
    expect(url).not.toContain('PDB-');
  });

  it('returns null for a non-existent entry (404)', async () => {
    mockFetch({}, 404);
    expect(await validateRelatedDb('EMD-99999')).toBeNull();
  });

  it('returns null for an unrecognised format without hitting the network', async () => {
    mockFetch({});
    expect(await validateRelatedDb('nonsense')).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
