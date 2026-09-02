import { act, renderHook, waitFor } from '@testing-library/react';

import { fetchResource } from '@app/common/queries/fetchResource';
import { TEM_API } from '../constants';
import { useSessionForm } from './useSessionForm';

jest.mock('@app/common/queries/fetchResource', () => ({
  fetchResource: jest.fn(),
  postResource: jest.fn(),
}));

const TODAY = '26sep02a';
const TOMO5_PLAN = { id: 1, name: 'tomo5 on krios1' };
const SERIALEM_PLAN = { id: 7, name: 'serialEM on krios1' };
// What the backend does: the chosen plan's name_prefix in front of the date.
const PLAN_PREFIX: Record<number, string> = { [TOMO5_PLAN.id]: '', [SERIALEM_PLAN.id]: 's' };

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
  return Promise.resolve(jsonResponse([]));
}

const mockedFetch = fetchResource as jest.MockedFunction<typeof fetchResource>;

async function mountForm() {
  const hook = renderHook(() => useSessionForm());
  await waitFor(() => expect(hook.result.current.state.name).toBe(TODAY));
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

    act(() => result.current.updateField('sessionPlanId', SERIALEM_PLAN.id));

    await waitFor(() => expect(result.current.state.name).toBe(`s${TODAY}`));
    expect(result.current.suggestedName).toBe(`s${TODAY}`);
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining(`${TEM_API.SUGGEST_NAME}?session_plan_id=${SERIALEM_PLAN.id}`)
    );
  });

  it('keeps a hand-typed name across a plan change', async () => {
    const { result } = await mountForm();

    act(() => result.current.updateField('name', 'mytestname'));
    act(() => result.current.updateField('sessionPlanId', SERIALEM_PLAN.id));

    await waitFor(() => expect(result.current.suggestedName).toBe(`s${TODAY}`));
    expect(result.current.state.name).toBe('mytestname');
  });

  it('re-suggests into an emptied name', async () => {
    const { result } = await mountForm();

    act(() => result.current.updateField('name', ''));
    act(() => result.current.updateField('sessionPlanId', TOMO5_PLAN.id));

    await waitFor(() => expect(result.current.state.name).toBe(TODAY));
  });

  it('follows the suggestion from one plan to the next while untouched', async () => {
    const { result } = await mountForm();

    act(() => result.current.updateField('sessionPlanId', SERIALEM_PLAN.id));
    await waitFor(() => expect(result.current.state.name).toBe(`s${TODAY}`));

    act(() => result.current.updateField('sessionPlanId', TOMO5_PLAN.id));
    await waitFor(() => expect(result.current.state.name).toBe(TODAY));
  });
});
