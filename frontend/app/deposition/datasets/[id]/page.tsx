'use client';

import { useParams } from 'next/navigation';
import NextLink from 'next/link';
import { Icon } from '@czi-sds/components';
import { Alert, Box, Chip, CircularProgress, Container, Link, Typography } from '@mui/material';

import { useDataset } from '../../hooks/useDataset';
import { STATUS_META } from '../../submissions/constants';
import { softChipSx } from '../../submissions/utils';
import { DatasetForm } from './DatasetForm';

export default function DatasetDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { data: dataset, isPending, isError } = useDataset(Number.isFinite(id) ? id : null);

  const renderBody = () => {
    if (!Number.isFinite(id)) {
      return <Alert severity="error">Invalid dataset id.</Alert>;
    }
    if (isPending) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      );
    }
    if (isError || !dataset) {
      return <Alert severity="error">Could not load this dataset. It may not exist or you may not have access.</Alert>;
    }

    const label = dataset.dataset_id ? `ds-${dataset.dataset_id}` : dataset.title || '(untitled draft)';
    const meta = STATUS_META[dataset.status];
    const readOnly = dataset.status !== 'draft';

    return (
      <>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            {label}
          </Typography>
          <Chip size="small" variant="outlined" label={meta.label} sx={softChipSx(meta.color)} />
        </Box>
        {dataset.dataset_id && dataset.title && (
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {dataset.title}
          </Typography>
        )}
        {readOnly && (
          <Alert severity="info" sx={{ mb: 3 }}>
            This dataset is {meta.label.toLowerCase()} and is read-only. Resume editing is only available for drafts.
          </Alert>
        )}
        <DatasetForm dataset={dataset} />
      </>
    );
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Link
        component={NextLink}
        href="/deposition/submissions"
        sx={{ display: 'inline-flex', alignItems: 'center', mb: 2 }}
        underline="hover"
      >
        <Icon sdsIcon="ChevronLeft" sdsSize="s" />
        Back to submissions
      </Link>
      {renderBody()}
    </Container>
  );
}
