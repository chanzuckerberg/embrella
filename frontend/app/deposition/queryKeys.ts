const root = ['depositions'] as const;

export const depositionKeys = {
  all: root,
  submissions: (scope?: 'mine') => [...root, 'submissions', scope ?? 'all'] as const,
  submissionsRoot: () => [...root, 'submissions'] as const,
  deposition: (id: number) => [...root, 'deposition', id] as const,
  dataset: (id: number) => [...root, 'dataset', id] as const,
  logs: (id: number, phase?: 'prep' | 'push') => [...root, 'dataset', id, 'logs', ...(phase ? [phase] : [])] as const,
};
