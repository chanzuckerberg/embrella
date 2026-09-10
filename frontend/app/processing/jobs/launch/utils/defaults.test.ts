import type { JSONSchema } from '@app/common/types/workflow';
import { applyUntouched, isSlurmField, missingRequired, splitDefaults, syncDynamicDefaults } from './defaults';

const schema: JSONSchema = {
  type: 'object',
  properties: {
    pixel_size: { type: 'number', title: 'Pixel size' },
    slurm_gpus: { type: 'integer', title: 'GPUs', 'x-slurm-directive': '--gpus' },
    slurm_time: { type: 'string', title: 'Time', 'x-compute-resource': true },
  },
};

describe('isSlurmField', () => {
  it('detects either slurm marker', () => {
    expect(isSlurmField(schema.properties.slurm_gpus)).toBe(true);
    expect(isSlurmField(schema.properties.slurm_time)).toBe(true);
    expect(isSlurmField(schema.properties.pixel_size)).toBe(false);
    expect(isSlurmField(undefined)).toBe(false);
  });
});

describe('splitDefaults', () => {
  it('routes by schema marker, unknown keys to params', () => {
    const { params, slurm } = splitDefaults(schema, { pixel_size: 1.9, slurm_gpus: 4, mystery: 'x' });

    expect(params).toEqual({ pixel_size: 1.9, mystery: 'x' });
    expect(slurm).toEqual({ slurm_gpus: 4 });
  });
});

describe('applyUntouched', () => {
  it('incoming overwrites previous defaults but not user edits', () => {
    const next = applyUntouched({ a: 1, b: 2 }, { a: 10, b: 20 }, new Set(['b']));

    expect(next).toEqual({ a: 10, b: 2 });
  });

  it('removes cleared keys unless touched', () => {
    const next = applyUntouched({ a: 1, b: 2 }, {}, new Set(['b']), ['a', 'b']);

    expect(next).toEqual({ b: 2 });
  });

  it('does not mutate prev', () => {
    const prev = { a: 1 };
    applyUntouched(prev, { a: 2 }, new Set());

    expect(prev).toEqual({ a: 1 });
  });
});

describe('missingRequired', () => {
  it('looks across buckets and dedupes', () => {
    const missing = missingRequired(['a', 'b', 'c', 'a'], { a: 1, b: '' }, { c: 0 });

    expect(missing).toEqual(['b']);
  });
});

describe('syncDynamicDefaults', () => {
  const listed = {
    gain_file_name: [
      { value: 'new.gain', label: 'new.gain' },
      { value: 'old.gain', label: 'old.gain' },
    ],
  };

  it('fills a blank field with the first option', () => {
    expect(syncDynamicDefaults({}, listed)).toEqual({ gain_file_name: 'new.gain' });
  });

  it('replaces a value the new session no longer lists', () => {
    expect(syncDynamicDefaults({ gain_file_name: 'from_other_session.gain' }, listed)).toEqual({
      gain_file_name: 'new.gain',
    });
  });

  it('keeps a value that is still listed', () => {
    expect(syncDynamicDefaults({ gain_file_name: 'old.gain' }, listed)).toEqual({});
  });

  it('keeps a typed absolute path', () => {
    expect(syncDynamicDefaults({ gain_file_name: '/elsewhere/ref.gain' }, listed)).toEqual({});
  });

  it('leaves a field alone when nothing is listed', () => {
    expect(syncDynamicDefaults({ gain_file_name: 'stale.gain' }, { gain_file_name: [] })).toEqual({});
  });
});
