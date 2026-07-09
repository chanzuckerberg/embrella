import { useQuery } from '@tanstack/react-query';

import { fetchSubmissions } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { SubmissionList } from '../types';

export function useSubmissions(scope?: 'mine') {
  return useQuery<SubmissionList>({
    queryKey: depositionKeys.submissions(scope),
    queryFn: () => fetchSubmissions(scope),
  });
}
