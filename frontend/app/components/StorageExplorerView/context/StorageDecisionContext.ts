import { createContext, useContext } from 'react';

import { DecisionTarget } from '../types';

interface StorageDecisionContextValue {
  /** Opens the set-status menu for a row. */
  openMenu: (anchor: HTMLElement, target: DecisionTarget) => void;
}

/**
 * Lets a row at any tier open the set-status menu.
 *
 * Through context rather than props because the run tier sits three components
 * below the table and nothing in between has any use for the handler — the same
 * convention SessionBrowserView uses for its grid-detail dialog.
 */
export const StorageDecisionContext = createContext<StorageDecisionContextValue | null>(null);

/** Null outside the provider, so a tier can render read-only in isolation (tests, Storybook). */
export function useStorageDecisions(): StorageDecisionContextValue | null {
  return useContext(StorageDecisionContext);
}
