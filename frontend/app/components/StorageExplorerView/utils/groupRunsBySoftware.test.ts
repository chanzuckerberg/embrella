import { StorageRunRow, StorageSessionData, StorageStatus } from '../types';
import { groupRunsBySoftware } from './groupRunsBySoftware';

function run(overrides: Partial<StorageRunRow> & { id: string; software: string }): StorageRunRow {
  return {
    run: { id: 1, name: 'run001' },
    procRunId: 1,
    directoryCount: 10,
    fileCount: 100,
    totalSizeBytes: 1000,
    totalSizeDisplay: '1000.00 B',
    lastModified: '2026-01-01T00:00:00Z',
    pathPrefix: `/base/${overrides.software}/26mar02a/run001`,
    status: 'unset' as StorageStatus,
    decidedAtPrefix: null,
    ...overrides,
  };
}

function session(runs: StorageRunRow[]): StorageSessionData {
  return {
    storageSession: { id: '26mar02a', name: '26mar02a' },
    sessionName: '26mar02a',
    registered: true,
    msiSessionId: 1,
    user: null,
    project: null,
    fsOwner: 'alice',
    cluster: 'czii',
    softwareCount: new Set(runs.map((r) => r.software)).size,
    runCount: runs.length,
    directoryCount: runs.reduce((sum, r) => sum + r.directoryCount, 0),
    fileCount: runs.reduce((sum, r) => sum + r.fileCount, 0),
    totalSizeBytes: runs.reduce((sum, r) => sum + r.totalSizeBytes, 0),
    totalSizeDisplay: '',
    lastModified: null,
    status: 'unset',
    runs,
  };
}

describe('groupRunsBySoftware', () => {
  it('groups runs by their on-disk software folder', () => {
    const groups = groupRunsBySoftware(
      session([
        run({ id: 'r1', software: 'aretomo3' }),
        run({ id: 'r2', software: 'denoise' }),
        run({ id: 'r3', software: 'aretomo3' }),
      ])
    );

    expect(groups.map((group) => group.software)).toEqual(['aretomo3', 'denoise']);
    expect(groups[0].runs).toHaveLength(2);
    expect(groups[1].runs).toHaveLength(1);
  });

  it('rolls sizes and counts up exactly', () => {
    // The whole reason the middle tier can live on the client: every figure it
    // shows is associative, so the rollup is exact rather than approximate.
    const runs = [
      run({ id: 'r1', software: 'aretomo3', totalSizeBytes: 300, directoryCount: 3, fileCount: 30 }),
      run({ id: 'r2', software: 'aretomo3', totalSizeBytes: 200, directoryCount: 2, fileCount: 20 }),
      run({ id: 'r3', software: 'denoise', totalSizeBytes: 500, directoryCount: 5, fileCount: 50 }),
    ];
    const data = session(runs);
    const groups = groupRunsBySoftware(data);

    for (const group of groups) {
      expect(group.totalSizeBytes).toBe(group.runs.reduce((sum, r) => sum + r.totalSizeBytes, 0));
      expect(group.directoryCount).toBe(group.runs.reduce((sum, r) => sum + r.directoryCount, 0));
      expect(group.fileCount).toBe(group.runs.reduce((sum, r) => sum + r.fileCount, 0));
    }

    // ...and the tier above reconciles with the tier below.
    expect(groups.reduce((sum, g) => sum + g.totalSizeBytes, 0)).toBe(data.totalSizeBytes);
    expect(groups.reduce((sum, g) => sum + g.directoryCount, 0)).toBe(data.directoryCount);
  });

  it('formats its own size the way the server formats the tiers around it', () => {
    const groups = groupRunsBySoftware(
      session([run({ id: 'r1', software: 'aretomo3', totalSizeBytes: 1024 * 1024 * 3 })])
    );

    expect(groups[0].totalSizeDisplay).toBe('3.00 MB');
  });

  it('takes the newest lastModified across the group', () => {
    const groups = groupRunsBySoftware(
      session([
        run({ id: 'r1', software: 'aretomo3', lastModified: '2025-03-01T00:00:00Z' }),
        run({ id: 'r2', software: 'aretomo3', lastModified: '2026-05-22T00:00:00Z' }),
        run({ id: 'r3', software: 'aretomo3', lastModified: null }),
      ])
    );

    expect(groups[0].lastModified).toBe('2026-05-22T00:00:00Z');
  });

  it('reports null lastModified when no run has one', () => {
    const groups = groupRunsBySoftware(session([run({ id: 'r1', software: 'aretomo3', lastModified: null })]));

    expect(groups[0].lastModified).toBeNull();
  });

  it('orders groups and their runs biggest first', () => {
    const groups = groupRunsBySoftware(
      session([
        run({ id: 'r1', software: 'denoise', totalSizeBytes: 100 }),
        run({ id: 'r2', software: 'aretomo3', totalSizeBytes: 200 }),
        run({ id: 'r3', software: 'aretomo3', totalSizeBytes: 900 }),
      ])
    );

    expect(groups.map((group) => group.software)).toEqual(['aretomo3', 'denoise']);
    expect(groups[0].runs.map((r) => r.totalSizeBytes)).toEqual([900, 200]);
  });

  it('excludes the session root from runCount but keeps its bytes', () => {
    // A "(session root)" leaf is files sitting directly under the session
    // directory. It is not a run, and the API's own runCount excludes it.
    const groups = groupRunsBySoftware(
      session([
        run({ id: 'r1', software: 'aretomo3', run: { id: null, name: '(session root)' }, totalSizeBytes: 50 }),
        run({ id: 'r2', software: 'aretomo3', totalSizeBytes: 100 }),
      ])
    );

    expect(groups[0].runCount).toBe(1);
    expect(groups[0].runs).toHaveLength(2);
    expect(groups[0].totalSizeBytes).toBe(150);
  });

  describe('status rollup', () => {
    it('collapses a unanimous group to the shared value', () => {
      const groups = groupRunsBySoftware(
        session([
          run({ id: 'r1', software: 'aretomo3', status: 'delete' }),
          run({ id: 'r2', software: 'aretomo3', status: 'delete' }),
        ])
      );

      expect(groups[0].status).toBe('delete');
    });

    it('reports mixed when runs disagree', () => {
      const groups = groupRunsBySoftware(
        session([
          run({ id: 'r1', software: 'aretomo3', status: 'delete' }),
          run({ id: 'r2', software: 'aretomo3', status: 'preserve' }),
        ])
      );

      expect(groups[0].status).toBe('mixed');
    });
  });

  it('namespaces group ids so they cannot collide with a run or session row', () => {
    const groups = groupRunsBySoftware(session([run({ id: 'r1', software: 'aretomo3' })]));

    expect(groups[0].id).toBe('storagesoftware-26mar02a-aretomo3');
  });

  it('returns nothing for a session with no runs', () => {
    expect(groupRunsBySoftware(session([]))).toEqual([]);
  });
});
