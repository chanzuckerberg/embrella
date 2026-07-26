import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { DemoQuickLinks } from './DemoQuickLinks';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

function renderWithFlags(flags: FEATURE_FLAG[]) {
  return render(
    <FeatureFlagsContext.Provider value={flags}>
      <DemoQuickLinks />
    </FeatureFlagsContext.Provider>
  );
}

describe('DemoQuickLinks', () => {
  it('renders nothing when the demo flag is off', () => {
    const { container } = renderWithFlags([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when only unrelated flags are on', () => {
    const { container } = renderWithFlags([FEATURE_FLAG.REVIEW]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the sample-data examples when the demo flag is on', () => {
    renderWithFlags([FEATURE_FLAG.DEMO]);
    expect(screen.getByText('Try it Out')).toBeInTheDocument();
    const labels = screen.getAllByRole('button').map((button) => button.textContent);
    expect(labels).toEqual(['Grid Example', 'Summary Example', 'Viewer Example']);
  });
});
