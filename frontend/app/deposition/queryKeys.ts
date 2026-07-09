const root = ['depositions'] as const;

export const depositionKeys = {
  all: root,
  submissions: (scope?: 'mine') => [...root, 'submissions', scope ?? 'all'] as const,
};