import { createElement, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook } from '@testing-library/react';

import { annotatedRefetchInterval, useTomogramSelectionCounts } from './useSources';
import type { Dataset } from '../types';

it('sums selected and available counts across AreTomo and denoise sources', () => {
  const client = new QueryClient();
  client.setQueryData(['deposition', 'sources', 'tomo-count', 'session', 'run001'], 291);
  client.setQueryData(['deposition', 'sources', 'denoise-count', 'session', 'run002'], 120);
  const dataset = {
    tomogram_subset_mode: 'custom',
    sessions: [
      {
        id: 1,
        msi_session: 1,
        msi_session_name: 'session',
        aretomo_run_name: 'run001',
        denoise_run_name: 'run002',
        subset_selection: ['position1', 'position2'],
      },
    ],
  } as Dataset;
  const wrapper = ({ children }: { children: ReactNode }) => createElement(QueryClientProvider, { client }, children);
  const { result, unmount } = renderHook(() => useTomogramSelectionCounts(dataset), { wrapper });
  expect(result.current).toEqual({ selected: 4, total: 411 });
  unmount();
  client.clear();
});

describe('annotatedRefetchInterval', () => {
  it('polls (5s) while a completed response is not yet scanned', () => {
    expect(annotatedRefetchInterval({ count: 0, scanned: false })).toBe(5000);
  });

  it('stops once the scan has completed', () => {
    expect(annotatedRefetchInterval({ count: 3, scanned: true })).toBe(false);
  });

  it('stops before the first response (no data yet)', () => {
    expect(annotatedRefetchInterval(undefined)).toBe(false);
  });

  it('stops on a terminal error even if the last data was unscanned', () => {
    expect(annotatedRefetchInterval({ count: 0, scanned: false }, true)).toBe(false);
  });
});
