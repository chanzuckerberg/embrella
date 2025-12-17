import { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Skeleton, Chip, Stack } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import StorageIcon from '@mui/icons-material/Storage';

import { DirectoryStats, ORIGIN_COLORS, ORIGIN_LABELS, STATUS_LABELS } from '../types';
import { fetchDirectoryStats } from '../api';

interface DirectoryStatsCardProps {
  surveyId: number | null;
}

/**
 * Card displaying aggregate statistics for the selected survey.
 */
export const DirectoryStatsCard = ({ surveyId }: DirectoryStatsCardProps) => {
  const [stats, setStats] = useState<DirectoryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!surveyId) {
      setStats(null);
      return;
    }

    const loadStats = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchDirectoryStats(surveyId);
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [surveyId]);

  if (!surveyId) {
    return null;
  }

  if (loading) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {[1, 2, 3, 4].map((i) => (
              <Box key={i} sx={{ flex: 1 }}>
                <Skeleton variant="rectangular" height={80} />
              </Box>
            ))}
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography color="error">{error}</Typography>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {/* Total Stats */}
          <Box sx={{ flex: '1 1 200px', minWidth: 200 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Total Storage
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <StorageIcon color="primary" />
                <Typography variant="h5">{stats.totals.total_size_display}</Typography>
              </Box>
              <Stack direction="row" spacing={2}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <FolderIcon fontSize="small" color="action" />
                  <Typography variant="body2">{stats.totals.directory_count} dirs</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <InsertDriveFileIcon fontSize="small" color="action" />
                  <Typography variant="body2">{stats.totals.total_files.toLocaleString()} files</Typography>
                </Box>
              </Stack>
            </Box>
          </Box>

          {/* By Origin */}
          <Box sx={{ flex: '1 1 300px', minWidth: 280 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              By Origin
            </Typography>
            <Stack spacing={1}>
              {stats.by_origin.map((item) => (
                <Box key={item.origin} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Chip
                    label={ORIGIN_LABELS[item.origin] || item.origin}
                    size="small"
                    sx={{ backgroundColor: ORIGIN_COLORS[item.origin] || '#9e9e9e', color: '#fff', minWidth: 120 }}
                  />
                  <Typography variant="body2">{item.total_size_display}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.directory_count} dirs
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Box>

          {/* By Status */}
          <Box sx={{ flex: '1 1 350px', minWidth: 320 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              By Status
            </Typography>
            <Stack spacing={1}>
              {stats.by_status.map((item) => (
                <Box
                  key={item.preserve_status}
                  sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <Chip
                    label={STATUS_LABELS[item.preserve_status] || item.preserve_status}
                    size="small"
                    variant="outlined"
                    sx={{ minWidth: 80 }}
                  />
                  <Typography variant="body2">{item.total_size_display}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.directory_count} dirs / {item.total_files.toLocaleString()} files
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
