'use client';

import { useContext } from 'react';
import { IconButton } from '@mui/material';
import { AccountTree as AccountTreeIcon } from '@mui/icons-material';
import { CDPP_WEB_PATH } from '@app/common/constants/constants';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { Job } from '../types';

/**
 * The cdpp-web pipeline id of a cdpp job, `embrella-<session>-<cdpp run>`, or null for any other job.
 *
 * cdpp-web lists Embrella-launched pipelines under this id. The cdpp processor records its own
 * run in `parameters._cdpp.cdpp_run`, on the cdpp run's execution and on each per-tree execution
 * it creates. All rows of one cdpp job therefore resolve to the same pipeline, whichever
 * execution the row was built from.
 */
export const cdppPipelineId = (job: Pick<Job, 'session' | 'parameters'>): string | null => {
  const cdpp = job.parameters?._cdpp;
  if (!job.session || !cdpp || typeof cdpp !== 'object') return null;
  const run = (cdpp as Record<string, unknown>).cdpp_run;
  return typeof run === 'string' && run ? `embrella-${job.session}-${run}` : null;
};

export const cdppWebPipelineUrl = (job: Pick<Job, 'session' | 'parameters'>): string | null => {
  const id = cdppPipelineId(job);
  return id ? `${CDPP_WEB_PATH}pipelines/${encodeURIComponent(id)}` : null;
};

interface CdppWebLinkProps {
  job: Job;
}

/** Opens a cdpp job's pipeline in cdpp-web. Renders nothing without the cdpp-web flag or for other jobs. */
export const CdppWebLink: React.FC<CdppWebLinkProps> = ({ job }) => {
  const featureFlags = useContext(FeatureFlagsContext);
  const href = cdppWebPipelineUrl(job);
  if (!href || !featureFlags.includes(FEATURE_FLAG.CDPP_WEB)) return null;

  return (
    <IconButton
      component="a"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      size="small"
      color="primary"
      title="Open in cdpp-web"
      aria-label="Open in cdpp-web"
      sx={{ padding: '4px' }}
    >
      <AccountTreeIcon fontSize="small" />
    </IconButton>
  );
};
