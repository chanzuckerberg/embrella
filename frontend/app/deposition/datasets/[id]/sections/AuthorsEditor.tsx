'use client';

import { Button, Icon } from '@czi-sds/components';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import {
  Avatar,
  Box,
  Checkbox,
  Chip,
  FormControlLabel,
  IconButton,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { IdentifierField } from '../../../components/IdentifierField';
import type { AuthorEntry } from '../../../types';

const AVATAR_COLORS = ['#6C5CE7', '#00B894', '#0984E3', '#E17055', '#E84393', '#00CEC9'];

const initials = (name?: string) =>
  (name ?? '')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('') || '?';

const blankAuthor = (order: number): AuthorEntry => ({
  full_name: '',
  affiliation: '',
  orcid: '',
  is_corresponding: false,
  is_primary: false,
  author_list_order: order,
});

export function AuthorsEditor({
  authors,
  onChange,
  disabled = false,
}: {
  authors: AuthorEntry[];
  onChange: (authors: AuthorEntry[]) => void;
  disabled?: boolean;
}) {
  const renumber = (list: AuthorEntry[]) => list.map((a, i) => ({ ...a, author_list_order: i }));
  const patch = (i: number, next: Partial<AuthorEntry>) =>
    onChange(authors.map((a, idx) => (idx === i ? { ...a, ...next } : a)));
  const remove = (i: number) => onChange(renumber(authors.filter((_, idx) => idx !== i)));
  const add = () => onChange([...authors, blankAuthor(authors.length)]);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Author list
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {authors.length} {authors.length === 1 ? 'author' : 'authors'}
          </Typography>
        </Box>
        <Button sdsType="secondary" sdsStyle="outline" disabled={disabled} onClick={add}>
          + Add author
        </Button>
      </Box>

      {authors.length === 0 ? (
        <Box
          sx={{
            border: '1px dashed',
            borderColor: 'divider',
            borderRadius: 2,
            py: 6,
            px: 3,
            textAlign: 'center',
          }}
        >
          <Avatar sx={{ bgcolor: (t) => `${t.palette.primary.main}14`, color: 'primary.main', mx: 'auto', mb: 1.5 }}>
            <PersonOutlineIcon />
          </Avatar>
          <Typography sx={{ fontWeight: 700, mb: 0.5 }}>No authors added yet</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Add the author for this dataset or switch to “Same as deposition authors”.
          </Typography>
          <Button sdsType="primary" sdsStyle="solid" disabled={disabled} onClick={add}>
            + Add author
          </Button>
        </Box>
      ) : (
        <Stack spacing={2}>
          {authors.map((a, i) => (
            <Paper key={i} variant="outlined" sx={{ p: 2.5, borderRadius: 2, bgcolor: 'grey.50' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Avatar
                    sx={{
                      width: 25,
                      height: 25,
                      fontSize: 14,
                      mr: 2,
                      bgcolor: AVATAR_COLORS[i % AVATAR_COLORS.length],
                    }}
                  >
                    {initials(a.full_name)}
                  </Avatar>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: 0.5 }}>
                    AUTHOR {i + 1}
                  </Typography>
                  {a.is_primary && (
                    <Chip
                      label="Primary"
                      size="small"
                      sx={{
                        height: 22,
                        fontWeight: 600,
                        bgcolor: (t) => `${t.palette.primary.main}1f`,
                        color: 'primary.dark',
                      }}
                    />
                  )}
                  {a.is_corresponding && (
                    <Chip
                      label="Corresponding"
                      size="small"
                      sx={{
                        height: 22,
                        fontWeight: 600,
                        bgcolor: (t) => `${t.palette.success.main}1f`,
                        color: 'success.dark',
                      }}
                    />
                  )}
                </Box>
                {!disabled && (
                  <IconButton aria-label={`Remove author ${i + 1}`} size="small" onClick={() => remove(i)}>
                    <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
                  </IconButton>
                )}
              </Box>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2, mt: 5 }}>
                <TextField
                  label="Full name"
                  value={a.full_name ?? ''}
                  onChange={(e) => patch(i, { full_name: e.target.value })}
                  size="small"
                  fullWidth
                  disabled={disabled}
                />
                <TextField
                  label="Affiliation"
                  value={a.affiliation ?? ''}
                  onChange={(e) => patch(i, { affiliation: e.target.value })}
                  size="small"
                  fullWidth
                  disabled={disabled}
                />
              </Stack>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} mt={5} alignItems={{ sm: 'flex-start' }}>
                <IdentifierField
                  kind="orcid"
                  label="ORCID"
                  value={a.orcid ?? ''}
                  onChange={(v) => patch(i, { orcid: v })}
                  placeholder="0000-0000-0000-0000"
                  size="small"
                  sx={{ minWidth: 260 }}
                  disabled={disabled}
                />
                <Box
                  sx={{
                    ml: 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    flexWrap: 'nowrap',
                    minHeight: { sm: 30 },
                  }}
                >
                  <Link
                    href="https://orcid.org"
                    target="_blank"
                    rel="noopener"
                    variant="body2"
                    sx={{ whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 0.25 }}
                  >
                    ORCID <OpenInNewIcon sx={{ fontSize: 14 }} />
                  </Link>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <FormControlLabel
                      sx={{ whiteSpace: 'nowrap', ml: 2.5 }}
                      control={
                        <Checkbox
                          size="small"
                          checked={!!a.is_primary}
                          onChange={(e) => patch(i, { is_primary: e.target.checked })}
                          disabled={disabled}
                        />
                      }
                      label="Primary author"
                    />
                    <FormControlLabel
                      sx={{ whiteSpace: 'nowrap', mr: 0 }}
                      control={
                        <Checkbox
                          size="small"
                          checked={a.is_corresponding}
                          onChange={(e) => patch(i, { is_corresponding: e.target.checked })}
                          disabled={disabled}
                        />
                      }
                      label="Corresponding author"
                    />
                  </Box>
                </Box>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}
    </Box>
  );
}
