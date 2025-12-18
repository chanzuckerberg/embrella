'use client';

/**
 * ScriptPreviewModal - Modal for previewing SLURM script before submission
 *
 * Features:
 * - Displays rendered script with syntax highlighting
 * - Copy to clipboard functionality
 * - Download script as .sh file
 * - Loading and error states
 */

import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DownloadIcon from '@mui/icons-material/Download';
import { useState } from 'react';
import { Prism as SyntaxHighlighterBase } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Workaround for TypeScript compatibility issue with react-syntax-highlighter
const SyntaxHighlighter = SyntaxHighlighterBase as typeof SyntaxHighlighterBase & React.FC;

interface ScriptPreviewModalProps {
  open: boolean;
  onClose: () => void;
  scriptContent: string | null;
  isLoading: boolean;
  error: string | null;
  jobName?: string; // For download filename
}

export default function ScriptPreviewModal({
  open,
  onClose,
  scriptContent,
  isLoading,
  error,
  jobName = 'script',
}: ScriptPreviewModalProps) {
  const [copySuccess, setCopySuccess] = useState(false);

  const handleCopy = async () => {
    if (!scriptContent) return;

    try {
      await navigator.clipboard.writeText(scriptContent);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    if (!scriptContent) return;

    const blob = new Blob([scriptContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${jobName}.sh`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      PaperProps={{
        sx: {
          maxHeight: '85vh',
          width: '75rem',
          maxWidth: '90vw',
        },
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <span>SLURM Script Preview</span>
          <IconButton edge="end" color="inherit" onClick={onClose} aria-label="close" size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {isLoading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        )}

        {!!error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!!scriptContent && !isLoading && !error && (
          <>
            {copySuccess && (
              <Alert severity="success" sx={{ mb: 2 }}>
                Script copied to clipboard!
              </Alert>
            )}

            <Box
              sx={{
                borderRadius: 1,
                overflow: 'auto',
                maxHeight: 600,
                border: '1px solid #333',
              }}
            >
              <SyntaxHighlighter
                language="bash"
                style={vscDarkPlus}
                showLineNumbers
                wrapLines={false}
                customStyle={{
                  margin: 0,
                  fontSize: '0.9em',
                  lineHeight: 1.6,
                }}
              >
                {scriptContent}
              </SyntaxHighlighter>
            </Box>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button startIcon={<ContentCopyIcon />} onClick={handleCopy} disabled={!scriptContent || isLoading}>
          Copy to Clipboard
        </Button>
        <Button startIcon={<DownloadIcon />} onClick={handleDownload} disabled={!scriptContent || isLoading}>
          Download Script
        </Button>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
