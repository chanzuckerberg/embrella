'use client';

import { FormControlLabel, Radio, RadioGroup, Typography } from '@mui/material';

import { SectionCard } from './SectionCard';

export function Authors({
  sameAsDeposition,
  onChangeSameAsDeposition,
  readOnly,
  innerRef,
}: {
  sameAsDeposition: boolean;
  onChangeSameAsDeposition: (value: boolean) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard title="Authors" sectionKey="authors" innerRef={innerRef}>
      <RadioGroup
        value={sameAsDeposition ? 'same' : 'custom'}
        onChange={(e) => onChangeSameAsDeposition(e.target.value === 'same')}
      >
        <FormControlLabel
          value="same"
          control={<Radio size="small" />}
          label="Same as deposition authors"
          disabled={readOnly}
        />
        <FormControlLabel
          value="custom"
          control={<Radio size="small" />}
          label="Customize authors"
          disabled={readOnly}
        />
      </RadioGroup>
      {!sameAsDeposition && (
        <Typography variant="body2" color="text.secondary">
          Custom author editing is added with the shared AuthorTable (#1003).
        </Typography>
      )}
    </SectionCard>
  );
}
