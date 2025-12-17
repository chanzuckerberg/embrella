'use client';

import { useState, useEffect, useContext } from 'react';
import { UserContext } from '@app/common/context/UserProvider';
import { DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';

interface RecentJob {
  jobId: string;
  jobName: string;
  status: string;
  submittedAt: string | null;
  duration: string | null;
  cluster: string;
}

interface DashboardData {
  recentJobs: RecentJob[];
  isLoading: boolean;
  error: string | null;
}

export const useDashboardData = (): DashboardData => {
  const user = useContext(UserContext);
  // For testing with a different user, uncomment:
  // const user = { ...useContext(UserContext), username: 'reza.paraan' };
  const [recentJobs, setRecentJobs] = useState<RecentJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch user's most recent completed/failed jobs
        // API expects flat array of { category, value } objects for filters, pagination, and sort
        const recentJobsQueryArr: { category: string; value: unknown }[] = [
          { category: 'status', value: ['Completed', 'Failed', 'Cancelled'] },
          { category: 'page', value: [1] },
          { category: 'pageSize', value: [5] },
          { category: 'sort', value: ['submittedAt'] },
          { category: 'asc', value: [false] },
        ];
        if (user?.username) {
          recentJobsQueryArr.push({ category: 'user', value: [user.username] });
        }
        const recentJobsQuery = encodeURIComponent(JSON.stringify(recentJobsQueryArr));
        const recentJobsUrl = `${DJANGO_URL}/workflow/v1/jobs/?cluster_id=czii&q=${recentJobsQuery}`;
        const recentJobsResponse = await fetchResource(recentJobsUrl);
        const recentJobsData = await recentJobsResponse.json();

        const jobs: RecentJob[] = (recentJobsData.result || [])
          .slice(0, 5) // Ensure max 5 jobs
          .map(
            (job: {
              job: { id: string };
              jobName: string;
              status: string;
              submittedAt: string | null;
              duration: string | null;
              cluster: string;
            }) => ({
              jobId: job.job.id,
              jobName: job.jobName,
              status: job.status,
              submittedAt: job.submittedAt,
              duration: job.duration,
              cluster: job.cluster,
            })
          );

        setRecentJobs(jobs);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [user?.username]);

  return { recentJobs, isLoading, error };
};
