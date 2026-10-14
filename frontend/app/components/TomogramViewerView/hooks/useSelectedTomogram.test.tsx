import { act, renderHook, waitFor } from '@testing-library/react';
import { withNuqsTestingAdapter, OnUrlUpdateFunction } from 'nuqs/adapters/testing';
import { useSelectedTomogram } from './useSelectedTomogram';
import { ReviewTomogramSummary } from '../types';

const TOMOGRAMS: ReviewTomogramSummary[] = [
  { tomogramId: 'id-1', position: 'Position_1', status: 'pending' },
  { tomogramId: 'id-2', position: 'Position_2', status: 'accepted' },
];

const setup = (searchParams = '') => {
  const onUrlUpdate = jest.fn<ReturnType<OnUrlUpdateFunction>, Parameters<OnUrlUpdateFunction>>();
  // Queue reset runs in the adapter's mount effect, after the hook's normalize effect, and would drop it
  const { result } = renderHook(() => useSelectedTomogram(TOMOGRAMS), {
    wrapper: withNuqsTestingAdapter({ searchParams, onUrlUpdate, hasMemory: true, resetUrlUpdateQueueOnMount: false }),
  });
  return { result, onUrlUpdate };
};

const lastPosition = (onUrlUpdate: jest.Mock) => onUrlUpdate.mock.lastCall?.[0].searchParams.get('position');

describe('useSelectedTomogram', () => {
  it('defaults to the first tomogram and writes it to the URL', async () => {
    const { result, onUrlUpdate } = setup();

    expect(result.current.selectedTomogramId).toBe('id-1');
    await waitFor(() => expect(lastPosition(onUrlUpdate)).toBe('Position_1'));
  });

  it('selects the tomogram matching ?position=', () => {
    const { result, onUrlUpdate } = setup('?position=Position_2');

    expect(result.current.selectedTomogramId).toBe('id-2');
    expect(onUrlUpdate).not.toHaveBeenCalled();
  });

  it('falls back to the first tomogram on an unknown position and corrects the URL', async () => {
    const { result, onUrlUpdate } = setup('?position=Nope');

    expect(result.current.selectedTomogramId).toBe('id-1');
    await waitFor(() => expect(lastPosition(onUrlUpdate)).toBe('Position_1'));
  });

  it('selectTomogram updates the URL with replace', async () => {
    const { result, onUrlUpdate } = setup('?position=Position_1');

    act(() => result.current.selectTomogram('id-2'));

    await waitFor(() => expect(result.current.selectedTomogramId).toBe('id-2'));
    expect(lastPosition(onUrlUpdate)).toBe('Position_2');
    expect(onUrlUpdate.mock.lastCall?.[0].options.history).toBe('replace');
  });
});
