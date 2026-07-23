'use client';

import { FormControlLabel, Radio, RadioGroup } from '@mui/material';

import type { AuthorRef } from '../../../types';
import { AuthorTable } from '../../../depositions/AuthorTable';
import { SectionCard } from './SectionCard';

export function Authors({
  sameAsDeposition,
  onChangeSameAsDeposition,
  authors,
  onChangeAuthors,
  readOnly,
  innerRef,
}: {
  sameAsDeposition: boolean;
  onChangeSameAsDeposition: (value: boolean) => void;
  authors: AuthorRef[];
  onChangeAuthors: (authors: AuthorRef[]) => void;
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
        <AuthorTable authors={authors} onChange={onChangeAuthors} disabled={readOnly} />
      )}
    </SectionCard>
  );
}
