import { act, renderHook } from '@testing-library/react';
import { StrictMode } from 'react';

import { useDraftAutoSave } from './useDraftAutoSave';
import { updateDataset } from '../services/depositionApi';
import { patchResource } from '@app/common/queries/fetchResource';

jest.mock('@app/common/queries/fetchResource', () => ({ patchResource: jest.fn() }));

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
    const { result } = renderHook(() => useDraftAutoSave('initial', save), { wrapper: StrictMode });

    let succeeded = false;
    await act(async () => {
      succeeded = await result.current.saveNow();
    });

    expect(succeeded).toBe(true);
    expect(save).not.toHaveBeenCalled();
    expect(result.current.isDirty).toBe(false);
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

  it('keeps unsaved edits and the unload warning until a retry succeeds', async () => {
    const save = jest
      .fn<Promise<void>, [string]>()
      .mockRejectedValueOnce(new Error('network error'))
      .mockResolvedValueOnce(undefined);
    const { result, rerender } = renderHook(({ data }) => useDraftAutoSave(data, save), {
      initialProps: { data: 'initial' },
    });
    const unload = () => {
      const event = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    };
    expect(unload()).toBe(false);
    rerender({ data: 'edited' });
    expect(result.current.isDirty).toBe(true);
    expect(unload()).toBe(true);

    let firstSucceeded = true;
    await act(async () => {
      firstSucceeded = await result.current.saveNow();
    });
    expect(firstSucceeded).toBe(false);
    expect(result.current.status).toBe('error');
    expect(unload()).toBe(true);

    let retrySucceeded = false;
    await act(async () => {
      retrySucceeded = await result.current.saveNow();
    });

    expect(retrySucceeded).toBe(true);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenNthCalledWith(2, 'edited');
    expect(result.current.status).toBe('saved');
    expect(result.current.isDirty).toBe(false);
    expect(unload()).toBe(false);
  });
  it('preserves unsaved changes and the actionable API message on a 409 metadata lock', async () => {
    (patchResource as jest.Mock).mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Metadata is locked.' }),
    });
    const { result, rerender } = renderHook(
      ({ data }) => useDraftAutoSave(data, (title) => updateDataset(1, { title })),
      {
        initialProps: { data: 'initial' },
      }
    );
    rerender({ data: 'edited' });
    await act(async () => {
      expect(await result.current.saveNow()).toBe(false);
    });
    expect(result.current.isDirty).toBe(true);
    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe(
      'Metadata is locked. Reload the page to check its current status before editing.'
    );
    expect(result.current.lastSavedAt).toBeNull();
  });

  it('keeps the unload warning after editing is locked, until changes are discarded', () => {
    const save = jest.fn().mockResolvedValue(undefined);
    const { result, rerender, unmount } = renderHook(({ data, enabled }) => useDraftAutoSave(data, save, { enabled }), {
      initialProps: { data: 'initial', enabled: true },
    });
    rerender({ data: 'edited', enabled: true });
    rerender({ data: 'edited', enabled: false });
    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(result.current.isDirty).toBe(true);

    act(() => result.current.discardChanges());
    const afterDiscard = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(afterDiscard);
    expect(afterDiscard.defaultPrevented).toBe(false);
    unmount();
    act(() => jest.runOnlyPendingTimers());
    expect(save).not.toHaveBeenCalled();
  });

  it('does not replay discarded edits after an in-flight save finishes', async () => {
    const pending = deferred<void>();
    const save = jest.fn().mockReturnValue(pending.promise);
    const { result, rerender, unmount } = renderHook(({ data }) => useDraftAutoSave(data, save), {
      initialProps: { data: 'initial' },
    });
    rerender({ data: 'first edit' });
    let saving!: Promise<boolean>;
    act(() => {
      saving = result.current.saveNow();
    });
    rerender({ data: 'later edit' });
    act(() => result.current.discardChanges());
    await act(async () => {
      pending.resolve(undefined);
      await saving;
    });
    unmount();
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith('first edit');
  });
});
