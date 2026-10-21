import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';

import { DatasetRow } from './DatasetRow';
import type { Dataset } from '../../types';

const draft: Dataset = {
  id: 1,
  deposition: 1,
  metadata_issues: [],
  dataset_id: 100,
  title: 'Draft dataset',
  status: 'draft',
  type: 'Tomos only',
  session_names: [],
  session_count: 0,
  updated_at: '2026-07-01T00:00:00Z',
};

const renderRow = (isOwner: boolean, dataset: Dataset = draft) =>
  render(
    <table>
      <tbody>
        <DatasetRow dataset={dataset} isOwner={isOwner} />
      </tbody>
    </table>
  );

describe('DatasetRow ownership gating', () => {
  it('shows "Resume" on a draft the user owns', () => {
    renderRow(true);
    expect(screen.getByText('Resume')).toBeInTheDocument();
    expect(screen.queryByText('View')).not.toBeInTheDocument();
  });

  it('shows "View" (not "Resume") on a draft the user does not own', () => {
    renderRow(false);
    expect(screen.getByText('View')).toBeInTheDocument();
    expect(screen.queryByText('Resume')).not.toBeInTheDocument();
  });
});

it('shows View for a failed dataset that requires confirmation before editing', () => {
  renderRow(true, { ...draft, status: 'failed' });
  expect(screen.getByText('View')).toBeInTheDocument();
  expect(screen.queryByText('Resume')).not.toBeInTheDocument();
});
