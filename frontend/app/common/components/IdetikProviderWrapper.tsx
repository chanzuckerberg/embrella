'use client';

import { IdetikProvider } from '@idetik/react';
import { ReactNode } from 'react';

export function IdetikProviderWrapper({ children }: { children: ReactNode }) {
  return <IdetikProvider>{children}</IdetikProvider>;
}
