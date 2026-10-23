import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { Job } from '../types';
import { CdppWebLink, cdppPipelineId } from './CdppWebLink';

const job = (overrides: Partial<Job>): Job => ({
  job: { id: 1234, name: 'cdpp', url: '' },
  jobName: 'cdpp',
  user: 'someone',
  status: 'Running',
  timeUsed: '1:00',
  timeLeft: '1:00:00',
  nodes: '1',
  partition: 'cpu',
  nodeList: 'node1',
  cluster: 'czii',
  submittedAt: null,
  parameters: null,
  errorMessage: null,
  isWorkflowLaunched: true,
  ...overrides,
});

// The cdpp run's own execution, and a tree execution the cdpp processor records for the same job.
const CDPP_JOB = job({
  processor: 'cdpp',
  session: '26jul16a',
  parameters: { cluster_id: 'czii', _cdpp: { cdpp_run: 'run001', trees: { isonet2: 'run003' } } },
});
const TREE_JOB = job({
  processor: 'isonet2',
  session: '26jul16a',
  parameters: { cluster_id: 'czii', _cdpp: { cdpp_run: 'run001', tree: 'isonet2' } },
});

function renderWithFlags(flags: FEATURE_FLAG[], row: Job) {
  return render(
    <FeatureFlagsContext.Provider value={flags}>
      <CdppWebLink job={row} />
    </FeatureFlagsContext.Provider>
  );
}

describe('cdppPipelineId', () => {
  it('names the pipeline after the session and the cdpp run', () => {
    expect(cdppPipelineId(CDPP_JOB)).toBe('embrella-26jul16a-run001');
  });

  it('resolves a tree execution to its cdpp run, not to the tree run', () => {
    expect(cdppPipelineId(TREE_JOB)).toBe('embrella-26jul16a-run001');
  });

  it('is null for jobs that are not cdpp jobs or lack the session or run', () => {
    expect(
      cdppPipelineId(job({ processor: 'aretomo3', session: '26jul16a', parameters: { run: 'run001' } }))
    ).toBeNull();
    expect(cdppPipelineId(job({ session: '26jul16a', parameters: null }))).toBeNull();
    expect(cdppPipelineId({ ...CDPP_JOB, session: undefined })).toBeNull();
    expect(cdppPipelineId(job({ session: '26jul16a', parameters: { _cdpp: { cdpp_run: 7 } } }))).toBeNull();
  });
});

describe('CdppWebLink', () => {
  it('renders nothing when the cdpp-web flag is off', () => {
    const { container } = renderWithFlags([FEATURE_FLAG.COPICK_WEB], CDPP_JOB);
    expect(container).toBeEmptyDOMElement();
  });

  it('links a cdpp job to its pipeline in cdpp-web', () => {
    renderWithFlags([FEATURE_FLAG.CDPP_WEB], CDPP_JOB);
    expect(screen.getByRole('link', { name: 'Open in cdpp-web' })).toHaveAttribute(
      'href',
      '/pipeline/pipelines/embrella-26jul16a-run001'
    );
  });

  it('links a tree execution of a cdpp job to the same pipeline', () => {
    renderWithFlags([FEATURE_FLAG.CDPP_WEB], TREE_JOB);
    expect(screen.getByRole('link', { name: 'Open in cdpp-web' })).toHaveAttribute(
      'href',
      '/pipeline/pipelines/embrella-26jul16a-run001'
    );
  });

  it('renders nothing for other jobs', () => {
    const { container } = renderWithFlags([FEATURE_FLAG.CDPP_WEB], job({ processor: 'aretomo3', session: '26jul16a' }));
    expect(container).toBeEmptyDOMElement();
  });
});
