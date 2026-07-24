'use client';

import { Box, Divider, Radio, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';

import type { AuthorEntry } from '../../../types';
import { AuthorsEditor } from './AuthorsEditor';
import { SectionCard } from './SectionCard';

function ChoiceCard({
  selected,
  title,
  description,
  disabled,
  onSelect,
}: {
  selected: boolean;
  title: string;
  description: string;
  disabled?: boolean;
  onSelect: () => void;
}) {
  return (
    <Box
      role="radio"
      aria-checked={selected}
      onClick={disabled ? undefined : onSelect}
      sx={{
        display: 'flex',
        gap: 1,
        p: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        bgcolor: selected ? (t) => alpha(t.palette.primary.main, 0.06) : 'background.paper',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <Radio size="small" checked={selected} disabled={disabled} sx={{ p: 0, mt: '2px' }} />
      <Box>
        <Typography sx={{ fontWeight: 700 }}>{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </Box>
    </Box>
  );
}

export function Authors({
  sameAsDeposition,
  onChangeSameAsDeposition,
  depositionAuthorCount,
  authors,
  onChangeAuthors,
  readOnly,
  innerRef,
}: {
  sameAsDeposition: boolean;
  onChangeSameAsDeposition: (value: boolean) => void;
  depositionAuthorCount?: number;
  authors: AuthorEntry[];
  onChangeAuthors: (authors: AuthorEntry[]) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  const authorNoun = depositionAuthorCount === 1 ? 'author' : 'authors';
  const sameDescription =
    depositionAuthorCount == null
      ? "Reuse the deposition's author list."
      : `Reuse the ${depositionAuthorCount} ${authorNoun} from the deposition.`;
  return (
    <SectionCard title="Authors" sectionKey="authors" innerRef={innerRef}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
        <ChoiceCard
          selected={sameAsDeposition}
          title="Same as deposition authors"
          description={sameDescription}
          disabled={readOnly}
          onSelect={() => onChangeSameAsDeposition(true)}
        />
        <ChoiceCard
          selected={!sameAsDeposition}
          title="Customize authors"
          description="Curate a dataset-specific author list."
          disabled={readOnly}
          onSelect={() => onChangeSameAsDeposition(false)}
        />
      </Box>
      {!sameAsDeposition && (
        <>
          <Divider />
          <AuthorsEditor authors={authors} onChange={onChangeAuthors} disabled={readOnly} />
        </>
      )}
    </SectionCard>
  );
}
