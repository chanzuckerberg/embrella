import { searchOntology, validateOntologyId } from './ols';

const DOC = {
  obo_id: 'UBERON:0000955',
  label: 'brain',
  synonym: ['encephalon'],
  iri: 'http://purl.obolibrary.org/obo/UBERON_0000955',
};

function mockFetch(docs: unknown[], ok = true, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    ok,
    status,
    json: async () => ({ response: { docs } }),
  }) as unknown as typeof fetch;
}

afterEach(() => jest.restoreAllMocks());

describe('OLS service', () => {
  it('maps search docs to terms', async () => {
    mockFetch([DOC]);
    const r = await searchOntology('brain', 'uberon');
    expect(r).toEqual([{ id: 'UBERON:0000955', label: 'brain', synonyms: ['encephalon'], iri: DOC.iri }]);
  });

  it('returns [] for a blank query without hitting the network', async () => {
    mockFetch([]);
    const r = await searchOntology('   ', 'uberon');
    expect(r).toEqual([]);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('drops docs missing obo_id or label', async () => {
    mockFetch([{ label: 'no id' }, { obo_id: 'CL:0000000' }]);
    expect(await searchOntology('x', 'cl')).toEqual([]);
  });

  it('validateOntologyId returns the exact match', async () => {
    mockFetch([DOC]);
    const t = await validateOntologyId('UBERON:0000955', 'uberon');
    expect(t?.label).toBe('brain');
  });

  it('validateOntologyId returns null when nothing matches', async () => {
    mockFetch([]);
    expect(await validateOntologyId('UBERON:9999999', 'uberon')).toBeNull();
  });

  it('validateOntologyId returns null for a blank id without hitting the network', async () => {
    mockFetch([]);
    expect(await validateOntologyId('', 'uberon')).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('throws on a non-ok response', async () => {
    mockFetch([], false, 500);
    await expect(searchOntology('brain', 'uberon')).rejects.toThrow(/OLS select failed: 500/);
  });

  it('searchOntology uses the fast /select endpoint with synonyms requested', async () => {
    mockFetch([DOC]);
    await searchOntology('brain', 'uberon');
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain('/ols4/api/select?');
    expect(url).toContain('fieldList=obo_id%2Clabel%2Csynonym%2Ciri');
  });

  it('validateOntologyId uses /search with an exact obo_id query', async () => {
    mockFetch([DOC]);
    await validateOntologyId('UBERON:0000955', 'uberon');
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain('/ols4/api/search?');
    expect(url).toContain('exact=true');
    expect(url).toContain('queryFields=obo_id');
  });
});
