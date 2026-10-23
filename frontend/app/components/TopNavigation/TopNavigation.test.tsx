import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { TopNavigation } from './TopNavigation';

jest.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

function renderWithFlags(flags: FEATURE_FLAG[]) {
  return render(
    <FeatureFlagsContext.Provider value={flags}>
      <TopNavigation />
    </FeatureFlagsContext.Provider>
  );
}

describe('TopNavigation', () => {
  it('hides the cdpp-web entry when the flag is off', () => {
    renderWithFlags([FEATURE_FLAG.COPICK_WEB]);
    expect(screen.getByRole('link', { name: 'Viewer' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Pipelines' })).not.toBeInTheDocument();
  });

  it('links to cdpp-web when the flag is on', () => {
    renderWithFlags([FEATURE_FLAG.CDPP_WEB]);
    expect(screen.getByRole('link', { name: 'Pipelines' })).toHaveAttribute('href', '/pipeline/');
    expect(screen.queryByRole('link', { name: 'Viewer' })).not.toBeInTheDocument();
  });
});
