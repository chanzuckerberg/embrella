import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';

import { GroupHeaderRow } from './GroupHeaderRow';
import type { Deposition } from '../../types';

const deposition = (is_owner: boolean): Deposition => ({
  id: 1,
  deposition_id: 10001,
  title: 'Test deposition',
  is_owner,
});

const renderHeader = (is_owner: boolean) =>
  render(
    <table>
      <tbody>
        <GroupHeaderRow
          deposition={deposition(is_owner)}
          open
          onToggle={() => {}}
          onAddDataset={() => {}}
        />
      </tbody>
    </table>,
  );

describe('GroupHeaderRow ownership gating', () => {
  it('shows "Add dataset" for the deposition owner', () => {
    renderHeader(true);
    expect(screen.getByText('Add dataset')).toBeInTheDocument();
  });

  it('hides "Add dataset" for non-owners', () => {
    renderHeader(false);
    expect(screen.queryByText('Add dataset')).not.toBeInTheDocument();
  });
});
