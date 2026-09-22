import { act, renderHook } from '@testing-library/react';

import { useDraftAutoSave } from './useDraftAutoSave';

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe('useDraftAutoSave', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => {
    act(() => jest.runOnlyPendingTimers());
    jest.useRealTimers();
  });

  it('skips the save when the data has not changed', async () => {
    const save = jest.fn<Promise<void>, [string]>().mockResolvedValue(undefined);
    const { result } = renderHook(() => useDraftAutoSave('initial', save));

    let succeeded = false;
    await act(async () => {
      succeeded = await result.current.saveNow();
    });

    expect(succeeded).toBe(true);
    expect(save).not.toHaveBeenCalled();
  });

  it('coalesces concurrent callers into one save', async () => {
    const pending = deferred<void>();
    const save = jest.fn<Promise<void>, [string]>().mockReturnValue(pending.promise);
    const { result, rerender } = renderHook(({ data }) => useDraftAutoSave(data, save), {
      initialProps: { data: 'initial' },
    });
    rerender({ data: 'edited' });

    let first!: Promise<boolean>;
    let second!: Promise<boolean>;
    act(() => {
      first = result.current.saveNow();
      second = result.current.saveNow();
    });

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith('edited');

    await act(async () => {
      pending.resolve(undefined);
      await Promise.all([first, second]);
    });

    expect(save).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('saved');
  });

  it('saves a newer edit before an in-flight save resolves', async () => {
    const firstRequest = deferred<void>();
    const save = jest
      .fn<Promise<void>, [string]>()
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce(undefined);
    const { result, rerender } = renderHook(({ data }) => useDraftAutoSave(data, save), {
      initialProps: { data: 'initial' },
    });
    rerender({ data: 'first edit' });

    let completed!: Promise<boolean>;
    act(() => {
      completed = result.current.saveNow();
    });
    expect(save).toHaveBeenNthCalledWith(1, 'first edit');

    rerender({ data: 'newer edit' });

    let succeeded = false;
    await act(async () => {
      firstRequest.resolve(undefined);
      succeeded = await completed;
    });

    expect(succeeded).toBe(true);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenNthCalledWith(2, 'newer edit');
    expect(result.current.status).toBe('saved');
  });

  it('keeps a failed revision available for retry', async () => {
    const save = jest
      .fn<Promise<void>, [string]>()
      .mockRejectedValueOnce(new Error('network error'))
      .mockResolvedValueOnce(undefined);
    const { result, rerender } = renderHook(({ data }) => useDraftAutoSave(data, save), {
      initialProps: { data: 'initial' },
    });
    rerender({ data: 'edited' });

    let firstSucceeded = true;
    await act(async () => {
      firstSucceeded = await result.current.saveNow();
    });
    expect(firstSucceeded).toBe(false);
    expect(result.current.status).toBe('error');

    let retrySucceeded = false;
    await act(async () => {
      retrySucceeded = await result.current.saveNow();
    });

    expect(retrySucceeded).toBe(true);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenNthCalledWith(2, 'edited');
    expect(result.current.status).toBe('saved');
  });
});
