import { SessionFilterConfig, SessionFilterId } from '../types';

/**
 * For the filters on the sidebar
 */
export const SESSION_FILTER_CONFIGS: SessionFilterConfig[][] = [
  [
    {
      filterCategory: 'project',
      filterId: SessionFilterId.PROJECT,
      label: 'Project',
    },
    {
      filterCategory: 'user',
      filterId: SessionFilterId.USER,
      label: 'User',
    },
    {
      filterCategory: 'processingSoftware',
      filterId: SessionFilterId.PROCESSING_SOFTWARE,
      label: 'Processing Software',
    },
  ],
  [
    {
      filterCategory: 'scope',
      filterId: SessionFilterId.SCOPE,
      label: 'Scope',
    },
    {
      filterCategory: 'workflow',
      filterId: SessionFilterId.WORKFLOW,
      label: 'Workflow',
    },
  ],
];

/** Categories the URL-synced TableStateProvider should track. */
export const SESSION_FILTER_CATEGORIES = ['project', 'user', 'processingSoftware', 'scope', 'workflow', 'search'];
