import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { SERVER_LOG_COOLDOWN_MS, useDatasetLogs } from './useDatasetLogs';
import * as api from '../services/depositionApi';
import type { JobState } from '../types';

jest.mock('../services/depositionApi');

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

const calls = () => (api.fetchDatasetLogs as jest.Mock).mock.calls.length;

beforeEach(() => {
  jest.clearAllMocks();
  (api.fetchDatasetLogs as jest.Mock).mockResolvedValue({ logs: 'tail', source: 'live' });
});

it('does not fetch when disabled (no job yet)', () => {
  renderHook(() => useDatasetLogs(7, { enabled: false }), { wrapper: wrapperFor(newClient()) });
  expect(api.fetchDatasetLogs).not.toHaveBeenCalled();
});

it('fetches only once when the first job enables the query', async () => {
  const { rerender, unmount } = renderHook(
    ({ state, enabled }: { state: JobState | undefined; enabled: boolean }) => useDatasetLogs(7, { state, enabled }),
    { wrapper: wrapperFor(newClient()), initialProps: { state: undefined as JobState | undefined, enabled: false } }
  );
  rerender({ state: 'prep_submitted', enabled: true });
  await waitFor(() => expect(calls()).toBe(1));
  unmount();
});

it('fetches once but does not poll when the job is inactive', async () => {
  jest.useFakeTimers();
  try {
    renderHook(() => useDatasetLogs(7, { state: 'prep_completed', pollIntervalMs: 50 }), {
      wrapper: wrapperFor(newClient()),
    });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    expect(calls()).toBe(1);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(200);
    });
    expect(calls()).toBe(1); // no polling
  } finally {
    jest.useRealTimers();
  }
});

it('polls on the given interval while the job is active', async () => {
  const { result } = renderHook(() => useDatasetLogs(7, { state: 'prep_running', pollIntervalMs: 40 }), {
    wrapper: wrapperFor(newClient()),
  });
  await waitFor(() => expect(result.current.data).toEqual({ logs: 'tail', source: 'live' }));
  await waitFor(() => expect(calls()).toBeGreaterThan(1));
});

it('refetches on a state change even when neither state polls', async () => {
  const { rerender } = renderHook(({ state }: { state: JobState }) => useDatasetLogs(7, { state }), {
    wrapper: wrapperFor(newClient()),
    initialProps: { state: 'prep_completed' },
  });
  await waitFor(() => expect(calls()).toBe(1)); // mount
  rerender({ state: 'completed' });
  await waitFor(() => expect(calls()).toBe(2)); // transition, not the interval
});

it('fetches the final tail again past the server cooldown when a running job finishes', async () => {
  jest.useFakeTimers();
  try {
    const { rerender } = renderHook(({ state }: { state: JobState }) => useDatasetLogs(7, { state }), {
      wrapper: wrapperFor(newClient()),
      initialProps: { state: 'prep_running' },
    });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    const afterMount = calls();

    rerender({ state: 'failed' }); // active -> terminal
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    const afterTransition = calls();
    expect(afterTransition).toBeGreaterThan(afterMount); // immediate refetch on the transition

    await act(async () => {
      await jest.advanceTimersByTimeAsync(SERVER_LOG_COOLDOWN_MS + 100);
    });
    expect(calls()).toBeGreaterThan(afterTransition); // one more past the cooldown for the final tail
  } finally {
    jest.useRealTimers();
  }
});

it('waits for a slow completion fetch before starting the final-read cooldown', async () => {
  jest.useFakeTimers();
  try {
    const { result, rerender, unmount } = renderHook(
      ({ state }: { state: JobState }) => {
        const query = useDatasetLogs(7, { state });
        return { data: query.data };
      },
      { wrapper: wrapperFor(newClient()), initialProps: { state: 'prep_running' } }
    );
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    await waitFor(() => expect(result.current.data?.logs).toBe('tail'));
    (api.fetchDatasetLogs as jest.Mock).mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(() => resolve({ logs: 'old tail', source: 'unavailable' }), 10000))
    );
    (api.fetchDatasetLogs as jest.Mock).mockResolvedValue({ logs: 'final tail', source: 'live' });
    rerender({ state: 'failed' });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(10000);
    });
    expect(calls()).toBe(2);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(SERVER_LOG_COOLDOWN_MS - 1);
    });
    expect(calls()).toBe(2);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(1);
    });
    expect(calls()).toBe(3);
    await waitFor(() => expect(result.current.data?.logs).toBe('final tail'));
    unmount();
  } finally {
    jest.useRealTimers();
  }
});

it('does not schedule a final read if unmounted while the completion fetch is pending', async () => {
  jest.useFakeTimers();
  try {
    const { rerender, unmount } = renderHook(({ state }: { state: JobState }) => useDatasetLogs(7, { state }), {
      wrapper: wrapperFor(newClient()),
      initialProps: { state: 'prep_running' },
    });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    (api.fetchDatasetLogs as jest.Mock).mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(() => resolve({ logs: 'tail', source: 'live' }), 10000))
    );
    rerender({ state: 'failed' });
    expect(calls()).toBe(2);
    unmount();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(10000 + SERVER_LOG_COOLDOWN_MS + 100);
    });
    expect(calls()).toBe(2);
  } finally {
    jest.useRealTimers();
  }
});

it('cancels the pending final read when prep restarts', async () => {
  jest.useFakeTimers();
  try {
    const { rerender, unmount } = renderHook(
      ({ state }: { state: JobState }) => useDatasetLogs(7, { state, pollIntervalMs: 1_000_000 }),
      { wrapper: wrapperFor(newClient()), initialProps: { state: 'prep_running' } }
    );
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    rerender({ state: 'failed' }); // schedules the post-completion read
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    rerender({ state: 'prep_submitted' }); // restart cancels it (and refetches for the new attempt)
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });
    const afterRestart = calls();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(SERVER_LOG_COOLDOWN_MS + 100);
    });
    expect(calls()).toBe(afterRestart); // the cancelled final read never fires
    unmount();
  } finally {
    jest.useRealTimers();
  }
});
