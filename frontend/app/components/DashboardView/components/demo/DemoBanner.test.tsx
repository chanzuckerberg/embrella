import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { DemoBanner } from './DemoBanner';

function renderWithFlags(flags: FEATURE_FLAG[]) {
  return render(
    <FeatureFlagsContext.Provider value={flags}>
      <DemoBanner />
    </FeatureFlagsContext.Provider>
  );
}

describe('DemoBanner', () => {
  it('renders nothing when the demo flag is off', () => {
    const { container } = renderWithFlags([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when only unrelated flags are on', () => {
    const { container } = renderWithFlags([FEATURE_FLAG.REVIEW]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the disclaimer when the demo flag is on', () => {
    renderWithFlags([FEATURE_FLAG.DEMO]);
    expect(screen.getByText(/trying out the Embrella demo/i)).toBeInTheDocument();
  });
});
