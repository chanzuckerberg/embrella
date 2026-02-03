'use client';

/**
 * CLIParserModal - Modal for importing AreTomo3 CLI commands
 *
 * Allows users to paste AreTomo3 CLI commands from prior runs and
 * auto-populate the launch form by parsing CLI flags.
 */

import { useState } from 'react';
import {
  TextField,
  Box,
  Typography,
  Alert,
  Collapse,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  List,
  ListItem,
  ListItemText,
  IconButton,
} from '@mui/material';
import { Dialog, DialogTitle, DialogContent, Button, Icon } from '@czi-sds/components';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import type { JSONSchema } from '@app/common/types/workflow';
import { parseCLICommand, getIgnoredReasonDescription } from '../utils/cliParser';
import type { ParsedCLIResult } from '../utils/cliParser';

interface CLIParserModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (params: Record<string, unknown>) => void;
  schema: JSONSchema;
}

export default function CLIParserModal({ open, onClose, onApply, schema }: CLIParserModalProps) {
  const [cliText, setCliText] = useState('');
  const [parseResult, setParseResult] = useState<ParsedCLIResult | null>(null);
  const [showIgnored, setShowIgnored] = useState(false);

  const handleParse = () => {
    const result = parseCLICommand(cliText, schema);
    setParseResult(result);
    setShowIgnored(false);
  };

  const handleApply = () => {
    if (parseResult?.success) {
      onApply(parseResult.parsedParams);
      handleClose();
    }
  };

  const handleClose = () => {
    setCliText('');
    setParseResult(null);
    setShowIgnored(false);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to parse
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleParse();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} sdsSize="m">
      <DialogTitle title="Import AreTomo3 CLI Command" onClose={handleClose} />
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {/* Instructions */}
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Paste your AreTomo3 command below to auto-fill the form parameters. The parser will extract recognized flags
            and ignore shell syntax like redirects and pipes.
          </Typography>

          {/* CLI Text Input */}
          <TextField
            multiline
            rows={6}
            fullWidth
            placeholder={`Example:
/path/to/AreTomo3 \\
  -PixSize 1.540 -kV 300 \\
  -AtBin 3.25 6.49 6.49 \\
  -Wbp 1 -FlipVol 1 -VolZ 1600 \\
  2>/dev/null`}
            value={cliText}
            onChange={(e) => setCliText(e.target.value)}
            onKeyDown={handleKeyDown}
            sx={{ mt: 2 }}
            slotProps={{
              input: {
                sx: {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                },
              },
            }}
          />

          {/* Parse Button */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2, gap: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', mr: 1 }}>
              Ctrl+Enter to parse
            </Typography>
            <Button sdsType="secondary" sdsStyle="rounded" onClick={handleParse} disabled={!cliText.trim()}>
              Parse
            </Button>
          </Box>

          {/* Parse Results */}
          {parseResult && (
            <Box sx={{ mt: 3 }}>
              {/* Warnings */}
              {parseResult.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {parseResult.warnings.map((warning, i) => (
                    <div key={i}>{warning}</div>
                  ))}
                </Alert>
              )}

              {/* Recognized Parameters */}
              {parseResult.parsedDetails.length > 0 && (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Icon sdsIcon="CheckCircle" sdsSize="s" color="success" />
                    <Typography variant="subtitle2">
                      Recognized Parameters ({parseResult.parsedDetails.length})
                    </Typography>
                  </Box>

                  <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Parameter</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>CLI Flag</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Value</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {parseResult.parsedDetails.map((param, index) => (
                          <TableRow key={index}>
                            <TableCell>{param.title}</TableCell>
                            <TableCell>
                              <code style={{ fontSize: '0.8rem' }}>{param.cliFlag}</code>
                            </TableCell>
                            <TableCell>
                              <code style={{ fontSize: '0.8rem' }}>{param.rawValue || '(flag present)'}</code>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              )}

              {/* Ignored Tokens */}
              {parseResult.ignoredTokens.length > 0 && (
                <Box>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      cursor: 'pointer',
                      '&:hover': { opacity: 0.8 },
                    }}
                    onClick={() => setShowIgnored(!showIgnored)}
                  >
                    <Icon sdsIcon="InfoCircle" sdsSize="s" color="gray" />
                    <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                      Ignored ({parseResult.ignoredTokens.length})
                    </Typography>
                    <IconButton size="small" sx={{ ml: 0.5 }}>
                      {showIgnored ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                    </IconButton>
                  </Box>

                  <Collapse in={showIgnored}>
                    <Paper variant="outlined" sx={{ mt: 1, maxHeight: 150, overflow: 'auto' }}>
                      <List dense disablePadding>
                        {parseResult.ignoredTokens.map((token, index) => (
                          <ListItem key={index} sx={{ py: 0.5 }}>
                            <ListItemText
                              primary={
                                <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace' }}>
                                  {token.token.length > 50 ? `${token.token.substring(0, 50)}...` : token.token}
                                </Typography>
                              }
                              secondary={getIgnoredReasonDescription(token.reason)}
                              slotProps={{
                                secondary: {
                                  sx: { fontSize: '0.75rem' },
                                },
                              }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Paper>
                  </Collapse>
                </Box>
              )}
            </Box>
          )}

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
            <Button sdsType="secondary" sdsStyle="rounded" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              onClick={handleApply}
              disabled={!parseResult?.success || parseResult.parsedDetails.length === 0}
            >
              Apply to Form
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
