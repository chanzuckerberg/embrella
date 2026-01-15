import { useEffect, useState } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  CircularProgress,
  Pagination,
  Paper,
} from '@mui/material';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import FolderIcon from '@mui/icons-material/Folder';
import ViewInArIcon from '@mui/icons-material/ViewInAr';

import { DirectoryFile, DirectoryFilesResponse } from '../types';
import { fetchDirectoryFiles } from '../api';

interface DirectoryFilesDrawerProps {
  directoryId: number;
  directoryPath: string;
}

const FILE_TYPE_ICONS: Record<string, React.ReactNode> = {
  file: <InsertDriveFileIcon fontSize="small" color="action" />,
  directory: <FolderIcon fontSize="small" color="primary" />,
  zarr: <ViewInArIcon fontSize="small" sx={{ color: '#9c27b0' }} />,
};

/**
 * Expandable row content showing files within a directory.
 * Fetches files on-demand from Parquet data via the backend.
 */
export const DirectoryFilesDrawer = ({ directoryId, directoryPath }: DirectoryFilesDrawerProps) => {
  const [data, setData] = useState<DirectoryFilesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  useEffect(() => {
    const loadFiles = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchDirectoryFiles(directoryId, { page, pageSize });
        setData(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load files');
      } finally {
        setLoading(false);
      }
    };

    loadFiles();
  }, [directoryId, page]);

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (loading && !data) {
    return (
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={20} />
        <Typography variant="body2">Loading files...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error" variant="body2">
          {error}
        </Typography>
      </Box>
    );
  }

  if (!data || data.files.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No files found in this directory.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
      <Typography variant="subtitle2" gutterBottom>
        Files in {directoryPath}
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell width={40}></TableCell>
              <TableCell>Filename</TableCell>
              <TableCell align="right" width={100}>
                Size
              </TableCell>
              <TableCell width={180}>Modified</TableCell>
              <TableCell width={80}>Mode</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.files.map((file: DirectoryFile, index: number) => (
              <TableRow key={`${file.path}-${index}`} hover>
                <TableCell>{FILE_TYPE_ICONS[file.type] || FILE_TYPE_ICONS.file}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {file.filename}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">{file.size_display}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="caption">{formatDate(file.mtime)}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                    {file.mode}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {data.total_pages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <Pagination
            count={data.total_pages}
            page={page}
            onChange={handlePageChange}
            size="small"
            disabled={loading}
          />
        </Box>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        Showing {data.files.length} of {data.total_count} files
      </Typography>
    </Box>
  );
};
