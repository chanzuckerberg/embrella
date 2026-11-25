import { addAll, removeAll, togglePick } from './selection';
import { PickedLocation, SelectMode } from './types';

const CAPACITY = 3;

const pick = (key: string): PickedLocation => ({ key, puckId: 1, puckName: '49', slot: 1 });

const keys = (picks: PickedLocation[]) => picks.map((p) => p.key);

describe('togglePick', () => {
  it('single mode replaces, and re-picking clears', () => {
    const one = togglePick([], pick('a'), SelectMode.Single, 1);

    expect(keys(togglePick(one, pick('b'), SelectMode.Single, 1))).toEqual(['b']);
    expect(togglePick(one, pick('a'), SelectMode.Single, 1)).toEqual([]);
  });

  it('multi mode toggles and ignores picks beyond capacity', () => {
    const full = [pick('a'), pick('b'), pick('c')];

    expect(keys(togglePick(full, pick('d'), SelectMode.Multi, CAPACITY))).toEqual(['a', 'b', 'c']);
    expect(keys(togglePick(full, pick('b'), SelectMode.Multi, CAPACITY))).toEqual(['a', 'c']);
  });
});

describe('addAll', () => {
  it('adds only new picks when they all fit', () => {
    expect(keys(addAll([pick('a')], [pick('a'), pick('b')], CAPACITY))).toEqual(['a', 'b']);
  });

  it('adds nothing when the box would overflow', () => {
    const picks = [pick('a'), pick('b')];

    expect(addAll(picks, [pick('c'), pick('d')], CAPACITY)).toBe(picks);
  });
});

describe('removeAll', () => {
  it('drops the given picks', () => {
    expect(keys(removeAll([pick('a'), pick('b'), pick('c')], [pick('a'), pick('c')]))).toEqual(['b']);
  });
});
