'use client';

import { useState } from 'react';
import { Button } from '@czi-sds/components';
import { Box, Typography } from '@mui/material';

import { YamlHighlight, EDITOR_BG } from './YamlHighlight';

export function YamlPreview({
  yaml,
  title,
  onClose,
  onChange,
}: {
  yaml: string;
  title?: string;
  onClose: () => void;
  onChange?: (yaml: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(yaml);
  const editable = Boolean(onChange);

  const startEdit = () => {
    setDraft(yaml);
    setEditing(true);
  };
  const save = () => {
    onChange?.(draft);
    setEditing(false);
  };
  const cancel = () => setEditing(false);

  let statusText = '';
  if (editing) statusText = 'editing - Save to apply to the fields';

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
          <Typography variant="caption" color="text.secondary" noWrap>
            {title}
            {title && statusText ? ' · ' : ''}
            {statusText}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
          {editable && !editing && (
            <Button sdsType="primary" sdsStyle="minimal" size="small" onClick={startEdit}>
              Edit
            </Button>
          )}
          {editing && (
            <>
              <Button sdsType="primary" sdsStyle="minimal" size="small" onClick={save}>
                Save
              </Button>
              <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={cancel}>
                Cancel
              </Button>
            </>
          )}
          {!editing && (
            <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={onClose}>
              Close
            </Button>
          )}
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', bgcolor: EDITOR_BG }}>
        {editing ? (
          <Box
            component="textarea"
            value={draft}
            spellCheck={false}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
            sx={{
              width: '100%',
              minHeight: 320,
              border: 'none',
              outline: 'none',
              resize: 'vertical',
              display: 'block',
              bgcolor: EDITOR_BG,
              color: '#c9d1d9',
              fontFamily: 'monospace',
              fontSize: '0.8125rem',
              lineHeight: 1.6,
              p: 1.5,
              tabSize: 2,
            }}
          />
        ) : (
          <YamlHighlight yaml={yaml} />
        )}
      </Box>
    </Box>
  );
}
