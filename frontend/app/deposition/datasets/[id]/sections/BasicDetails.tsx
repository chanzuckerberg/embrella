'use client';

import { TextField } from '@mui/material';

import { SectionCard } from './SectionCard';

export function BasicDetails({
  title,
  description,
  onChangeTitle,
  onChangeDescription,
  readOnly,
  innerRef,
}: {
  title: string;
  description: string;
  onChangeTitle: (value: string) => void;
  onChangeDescription: (value: string) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard title="Basic details" sectionKey="basic" innerRef={innerRef}>
      <TextField
        label="Title"
        value={title}
        onChange={(e) => onChangeTitle(e.target.value)}
        required
        fullWidth
        size="small"
        disabled={readOnly}
      />
      <TextField
        label="Description"
        value={description}
        onChange={(e) => onChangeDescription(e.target.value)}
        required
        multiline
        minRows={3}
        fullWidth
        size="small"
        disabled={readOnly}
        helperText="2–3 sentences"
        sx={{ '& textarea': { resize: 'vertical' } }}
      />
    </SectionCard>
  );
}
