import { SessionPlanOption } from '../types';
import { autoFill, pickTier, resolvePlan, tierOptions } from './planTiers';

const TOMO = 'TEM Tomography';
const SPA = 'TEM Single Tilt SPA';

const plan = (id: number, scope: string, software: string, camera: string, workflow = TOMO) =>
  ({ id, name: `${workflow} ${software} ${scope} ${camera}`, workflow, scope, software, camera }) as SessionPlanOption;

// CZII-like: two scopes, serialEM on both, tomo5 on krios1 only, one camera per scope+software.
const PLANS = [
  plan(1, 'krios1', 'tomo5', 'Falcon4i'),
  plan(7, 'krios1', 'serialEM', 'Falcon4i'),
  plan(8, 'krios2', 'serialEM', 'GatanCeltic'),
  plan(9, 'krios2', 'leginon', 'GatanCeltic', SPA),
];

describe('tierOptions', () => {
  it('offers distinct values narrowed by the tiers above', () => {
    expect(tierOptions(PLANS, {}, 'scope')).toEqual(['krios1', 'krios2']);
    expect(tierOptions(PLANS, { scope: 'krios2' }, 'software')).toEqual(['serialEM', 'leginon']);
    expect(tierOptions(PLANS, { scope: 'krios2', software: 'leginon' }, 'workflow')).toEqual([SPA]);
  });

  it('ignores tiers below the one asked for', () => {
    expect(tierOptions(PLANS, { scope: 'krios1', workflow: SPA }, 'software')).toEqual(['tomo5', 'serialEM']);
  });
});

describe('autoFill', () => {
  it('fills single-option tiers and stops at the first real choice', () => {
    const onlyKrios2 = PLANS.filter((p) => p.scope === 'krios2');
    expect(autoFill(onlyKrios2, {})).toEqual({ scope: 'krios2' });
    expect(autoFill(onlyKrios2, { scope: 'krios2', software: 'leginon' })).toEqual({
      scope: 'krios2',
      software: 'leginon',
      workflow: SPA,
      camera: 'GatanCeltic',
    });
  });

  it('pins the plan outright when only one exists', () => {
    expect(autoFill([PLANS[1]], {})).toEqual({
      scope: 'krios1',
      software: 'serialEM',
      workflow: TOMO,
      camera: 'Falcon4i',
    });
  });
});

describe('pickTier', () => {
  it('resets the tiers below the pick, then auto-fills what follows', () => {
    const before = { scope: 'krios1', software: 'tomo5', workflow: TOMO, camera: 'Falcon4i' };

    const after = pickTier(PLANS, before, 'software', 'serialEM');

    expect(after).toEqual({ scope: 'krios1', software: 'serialEM', workflow: TOMO, camera: 'Falcon4i' });
  });

  it('leaves a tier with several options open', () => {
    expect(pickTier(PLANS, {}, 'scope', 'krios1')).toEqual({ scope: 'krios1' });
    expect(pickTier(PLANS, {}, 'scope', 'krios2')).toEqual({ scope: 'krios2' });
  });

  it('clearing a tier clears everything below it', () => {
    const full = { scope: 'krios1', software: 'tomo5', workflow: TOMO, camera: 'Falcon4i' };
    expect(pickTier(PLANS, full, 'scope', undefined)).toEqual({});
  });
});

describe('resolvePlan', () => {
  it('is null until every tier is set', () => {
    expect(resolvePlan(PLANS, { scope: 'krios1', software: 'tomo5' })).toBeNull();
  });

  it('returns the plan the four tiers identify', () => {
    const selection = { scope: 'krios1', software: 'serialEM', workflow: TOMO, camera: 'Falcon4i' };
    expect(resolvePlan(PLANS, selection)?.id).toBe(7);
  });
});
