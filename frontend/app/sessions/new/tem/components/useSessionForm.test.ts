import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, PropsWithChildren } from 'react';

import { fetchResource } from '@app/common/queries/fetchResource';
import { TEM_API } from '../constants';
import { useSessionForm } from './useSessionForm';

jest.mock('@app/common/queries/fetchResource', () => ({
  fetchResource: jest.fn(),
  postResource: jest.fn(),
}));

const TODAY = '26sep02a';
const TOMO = 'TEM Tomography';
const TOMO5_PLAN = {
  id: 1,
  name: 'tomo5 on krios1',
  workflow: TOMO,
  scope: 'krios1',
  software: 'tomo5',
  camera: 'Falcon4i',
};
const SERIALEM_PLAN = {
  id: 7,
  name: 'serialEM on krios1',
  workflow: TOMO,
  scope: 'krios1',
  software: 'serialEM',
  camera: 'Falcon4i',
};
// What the backend does: the chosen plan's name_prefix in front of the date.
const PLAN_PREFIX: Record<number, string> = { [TOMO5_PLAN.id]: '', [SERIALEM_PLAN.id]: 's' };

const USER_ID = 5;
const DEFAULT_GRID = { id: 11, name: 'g11', display_name: 'Grid 11', is_default: true };
const OTHER_GRID = { id: 12, name: 'g12', display_name: 'Grid 12', is_default: false };
const MAGNIFICATION = { id: 3, nominal_mag: 50000, mode: 'SA', index: 0, scope__name: 'krios1', display: '50kx' };

const jsonResponse = (body: unknown) => ({ ok: true, json: async () => body }) as unknown as Response;

function fakeBackend(url: string): Promise<Response> {
  const { pathname, searchParams } = new URL(url, 'http://test');

  if (pathname === TEM_API.SUGGEST_NAME) {
    const planId = Number(searchParams.get('session_plan_id'));
    return Promise.resolve(jsonResponse({ suggested_name: `${PLAN_PREFIX[planId] ?? ''}${TODAY}` }));
  }
  if (pathname === TEM_API.FORM_OPTIONS) {
    return Promise.resolve(jsonResponse({ session_plans: [TOMO5_PLAN, SERIALEM_PLAN], projects: [] }));
  }
  if (pathname === TEM_API.USERS) {
    return Promise.resolve(jsonResponse({ users: [] }));
  }
  if (pathname === TEM_API.MAGNIFICATIONS) {
    return Promise.resolve(jsonResponse([MAGNIFICATION]));
  }
  if (pathname === TEM_API.GRIDS_BY_USER) {
    const grids = searchParams.get('user_id') === String(USER_ID) ? [OTHER_GRID, DEFAULT_GRID] : [];
    return Promise.resolve(jsonResponse(grids));
  }
  return Promise.resolve(jsonResponse([]));
}

const mockedFetch = fetchResource as jest.MockedFunction<typeof fetchResource>;

// A fresh client per mount: no cache shared between tests, no retries hiding failures.
function queryWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children);
  }
  return Wrapper;
}

async function mountForm() {
  const hook = renderHook(() => useSessionForm(), { wrapper: queryWrapper() });
  await waitFor(() => expect(hook.result.current.state.name).toBe(TODAY));
  await waitFor(() => expect(hook.result.current.isLoading).toBe(false));
  return hook;
}

beforeEach(() => {
  mockedFetch.mockReset();
  mockedFetch.mockImplementation(fakeBackend);
});

describe('useSessionForm suggested name', () => {
  it('starts with the unprefixed suggestion before a plan is chosen', async () => {
    const { result } = await mountForm();

    expect(result.current.suggestedName).toBe(TODAY);
    expect(mockedFetch).toHaveBeenCalledWith(expect.stringContaining(TEM_API.SUGGEST_NAME));
  });

  it('asks for the plan-specific suggestion and applies it to an untouched name', async () => {
    const { result } = await mountForm();

    act(() => result.current.selectSessionPlan(SERIALEM_PLAN.id));

    await waitFor(() => expect(result.current.state.name).toBe(`s${TODAY}`));
    expect(result.current.suggestedName).toBe(`s${TODAY}`);
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining(`${TEM_API.SUGGEST_NAME}?session_plan_id=${SERIALEM_PLAN.id}`)
    );
  });

  it('keeps a hand-typed name across a plan change', async () => {
    const { result } = await mountForm();

    act(() => result.current.updateField('name', 'mytestname'));
    act(() => result.current.selectSessionPlan(SERIALEM_PLAN.id));

    await waitFor(() => expect(result.current.suggestedName).toBe(`s${TODAY}`));
    expect(result.current.state.name).toBe('mytestname');
  });

  it('re-suggests into an emptied name', async () => {
    const { result } = await mountForm();

    act(() => result.current.updateField('name', ''));
    act(() => result.current.selectSessionPlan(TOMO5_PLAN.id));

    await waitFor(() => expect(result.current.state.name).toBe(TODAY));
  });

  it('follows the suggestion from one plan to the next while untouched', async () => {
    const { result } = await mountForm();

    act(() => result.current.selectSessionPlan(SERIALEM_PLAN.id));
    await waitFor(() => expect(result.current.state.name).toBe(`s${TODAY}`));

    act(() => result.current.selectSessionPlan(TOMO5_PLAN.id));
    await waitFor(() => expect(result.current.state.name).toBe(TODAY));
  });
});

describe('useSessionForm tiered plan choice', () => {
  it('pre-fills tiers with a single option and leaves the real choice open', async () => {
    const { result } = await mountForm();

    // Both plans are on krios1, so scope is filled; software is the first real choice.
    await waitFor(() => expect(result.current.planSelection).toEqual({ scope: 'krios1' }));
    expect(result.current.planTierOptions.software).toEqual(['tomo5', 'serialEM']);
    expect(result.current.state.sessionPlanId).toBeNull();
  });

  it('completing the tiers resolves the plan and prefixes the name', async () => {
    const { result } = await mountForm();
    await waitFor(() => expect(result.current.planSelection.scope).toBe('krios1'));

    act(() => result.current.selectPlanTier('software', 'serialEM'));

    // Workflow and camera each have one option left: auto-filled, so one click pins the plan.
    expect(result.current.planSelection).toEqual({
      scope: 'krios1',
      software: 'serialEM',
      workflow: TOMO,
      camera: 'Falcon4i',
    });
    expect(result.current.state.sessionPlanId).toBe(SERIALEM_PLAN.id);
    await waitFor(() => expect(result.current.state.name).toBe(`s${TODAY}`));
  });

  it('re-picking an upper tier clears the plan until the tiers below are chosen again', async () => {
    const { result } = await mountForm();
    await waitFor(() => expect(result.current.planSelection.scope).toBe('krios1'));
    act(() => result.current.selectPlanTier('software', 'serialEM'));
    expect(result.current.state.sessionPlanId).toBe(SERIALEM_PLAN.id);

    act(() => result.current.selectPlanTier('scope', 'krios1'));

    expect(result.current.planSelection).toEqual({ scope: 'krios1' });
    expect(result.current.state.sessionPlanId).toBeNull();
  });
});

describe('useSessionForm dependent lists', () => {
  it('selecting a plan loads its magnifications and clears the old pick', async () => {
    const { result } = await mountForm();
    act(() => result.current.updateField('magnificationId', 99));

    act(() => result.current.selectSessionPlan(SERIALEM_PLAN.id));

    await waitFor(() => expect(result.current.magnifications).toEqual([MAGNIFICATION]));
    expect(result.current.state.magnificationId).toBeNull();
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining(`${TEM_API.MAGNIFICATIONS}?session_plan_id=${SERIALEM_PLAN.id}`)
    );
  });

  it('clearing the plan empties the magnifications without a request', async () => {
    const magnificationCalls = () =>
      mockedFetch.mock.calls.filter(([url]) => String(url).includes(TEM_API.MAGNIFICATIONS)).length;
    const { result } = await mountForm();
    act(() => result.current.selectSessionPlan(SERIALEM_PLAN.id));
    await waitFor(() => expect(result.current.magnifications).toHaveLength(1));
    const calls = magnificationCalls();

    act(() => result.current.selectSessionPlan(null));

    expect(result.current.magnifications).toEqual([]);
    // The unprefixed name is re-requested for "no plan"; magnifications are not.
    expect(magnificationCalls()).toBe(calls);
  });

  it('selecting a user loads their grids and pre-selects the default one', async () => {
    const { result } = await mountForm();

    act(() => result.current.selectFilterUser(USER_ID));

    await waitFor(() => expect(result.current.state.gridId).toBe(DEFAULT_GRID.id));
    expect(result.current.state.filterUserId).toBe(USER_ID);
    expect(mockedFetch).toHaveBeenCalledWith(expect.stringContaining(`${TEM_API.GRIDS_BY_USER}?user_id=${USER_ID}`));
  });
});
