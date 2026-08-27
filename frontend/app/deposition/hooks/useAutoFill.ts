'use client';

import { useMutation } from '@tanstack/react-query';

import { autoFillSession } from '../services/depositionApi';
import type { DepositionSession } from '../types';

/**
 * Runs cryoetportalprep init for one session and returns it with tiltseries/tomogram
 */
export function useAutoFill(onFilled: (session: DepositionSession) => void) {
  return useMutation({
    mutationFn: (sessionId: number) => autoFillSession(sessionId),
    onSuccess: onFilled,
  });
}
