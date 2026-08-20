'use client';

import { useState } from 'react';
import { Box, Button, Typography } from '@mui/material';

import { YamlHighlight } from './YamlHighlight';

export function YamlPreview({
  yaml,
  title,
  readOnly,
  onClose,
  onApply,
}: {
  yaml: string;
  title?: string;
  readOnly: boolean;
  onClose: () => void;
  onApply: (text: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(yaml);

  const startEdit = () => {
    setDraft(yaml);
    setEditing(true);
  };
  const save = () => {
    onApply(draft);
    setEditing(false);
  };

  return (
    <Box
      sx={{
        position: 'sticky',
        top: 0,
        alignSelf: 'start',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 300px)',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          px: 1.5,
          py: 1,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
            dataprep_config.yaml
          </Typography>
          {title && (
            <Typography variant="caption" color="text.secondary" noWrap>
              {title}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
          {!readOnly &&
            (editing ? (
              <>
                <Button size="small" onClick={() => setEditing(false)} sx={{ textTransform: 'none' }}>
                  Cancel
                </Button>
                <Button size="small" variant="contained" onClick={save} sx={{ textTransform: 'none', fontWeight: 600 }}>
                  Save
                </Button>
              </>
            ) : (
              <Button size="small" onClick={startEdit} sx={{ textTransform: 'none', fontWeight: 600 }}>
                Edit
              </Button>
            ))}
          <Button size="small" onClick={onClose} sx={{ textTransform: 'none', color: 'text.secondary' }}>
            Close
          </Button>
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', bgcolor: '#0d1117' }}>
        {editing ? (
          <Box
            component="textarea"
            value={draft}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
            spellCheck={false}
            sx={{
              width: '100%',
              minHeight: 320,
              border: 'none',
              outline: 'none',
              resize: 'vertical',
              p: 2,
              bgcolor: '#0d1117',
              color: '#c9d1d9',
              fontSize: '0.8rem',
              lineHeight: 1.7,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            }}
          />
        ) : (
          <YamlHighlight yaml={yaml} />
        )}
      </Box>

      {editing && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ px: 1.5, py: 1, borderTop: '1px solid', borderColor: 'divider' }}
        >
          Editing the modeled fields. Save writes recognized keys back to the form; unknown keys are ignored.
        </Typography>
      )}
    </Box>
  );
}
