'use client';

import { useState, useEffect } from 'react';
import { Box, Typography, Paper, Skeleton } from '@mui/material';
import { Table, TableHeader, TableRow, CellHeader, CellComponent, Button } from '@czi-sds/components';
import { TableBody } from '@mui/material';
import { useRouter } from 'next/navigation';
import { DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';

interface RecentSession {
  id: number;
  name: string;
  projectName: string;
  createdAt: string;
}

interface RecentSessionsTableProps {
  isLoading?: boolean;
}

export const RecentSessionsTable = ({ isLoading: parentLoading }: RecentSessionsTableProps) => {
  const router = useRouter();
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      setIsLoading(true);
      try {
        // API expects flat array of { category, value } objects
        const queryArr = [
          { category: 'page', value: [1] },
          { category: 'sort', value: ['created_at'] },
          { category: 'asc', value: [false] },
        ];
        const query = encodeURIComponent(JSON.stringify(queryArr));
        const url = `${DJANGO_URL}/api/sessions/?q=${query}`;
        const response = await fetchResource(url);
        const data = await response.json();

        // API returns array directly, or wrapped in result/msiSession
        const sessionList = Array.isArray(data) ? data : data.result || data.msiSession || [];

        const recentSessions: RecentSession[] = sessionList
          .slice(0, 5)
          .map((session: { sessionId: number; sessionName: string; projectName: string; createdAt: string }) => ({
            id: session.sessionId,
            name: session.sessionName,
            projectName: session.projectName || '-',
            createdAt: session.createdAt,
          }));

        setSessions(recentSessions);
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSessions();
  }, []);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const loading = parentLoading || isLoading;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
          Most Recent Sessions
        </Typography>
        <Button sdsType="secondary" sdsStyle="square" size="small" onClick={() => router.push('/sessions/browse')}>
          View All
        </Button>
      </Box>

      <Paper elevation={1}>
        {loading ? (
          <Box sx={{ p: 2 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} variant="text" height={48} sx={{ mb: 1 }} />
            ))}
          </Box>
        ) : sessions.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">No recent sessions found</Typography>
          </Box>
        ) : (
          <Table>
            <TableHeader>
              <CellHeader>Session Name</CellHeader>
              <CellHeader>Project</CellHeader>
              <CellHeader>Created</CellHeader>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => (
                <TableRow
                  key={session.id}
                  onClick={() => (window.location.href = `${DJANGO_URL}/admin/tem/msisession/${session.id}/`)}
                  style={{ cursor: 'pointer' }}
                >
                  <CellComponent>
                    <span style={{ fontWeight: 500, color: '#6E4FF9' }}>{session.name}</span>
                  </CellComponent>
                  <CellComponent>{session.projectName}</CellComponent>
                  <CellComponent>{formatDate(session.createdAt)}</CellComponent>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
};
