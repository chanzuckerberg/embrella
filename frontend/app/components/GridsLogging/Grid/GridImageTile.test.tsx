import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { withNuqsTestingAdapter } from 'nuqs/adapters/testing';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { useGridImageUploads, useGridImages } from '@app/common/hooks/images/useGridImages';
import { testImage } from '@app/common/components/images/testImages';
import { GridImageTile } from './GridImageTile';

jest.mock('@app/common/hooks/images/useGridImages');
jest.mock('@app/components/GridDetailDialog/GridDetailDialog', () => ({
  GridDetailDialog: ({ open }: { open: boolean }) => (open ? <div role="dialog">grid dialog</div> : null),
}));

const mockImages = useGridImages as jest.Mock;
(useGridImageUploads as jest.Mock).mockReturnValue({
  uploads: [],
  add: jest.fn(),
  reject: jest.fn(),
  dismiss: jest.fn(),
});

function renderTile(flags: FEATURE_FLAG[] = [FEATURE_FLAG.IMAGES]) {
  const onUrlUpdate = jest.fn();
  render(
    <FeatureFlagsContext.Provider value={flags}>
      <GridImageTile gridId={7} />
    </FeatureFlagsContext.Provider>,
    { wrapper: withNuqsTestingAdapter({ onUrlUpdate }) }
  );
  return onUrlUpdate;
}

describe('GridImageTile', () => {
  it('renders nothing without the images flag', () => {
    mockImages.mockReturnValue({ data: [] });

    renderTile([]);

    expect(screen.queryByTestId('image-dropzone')).not.toBeInTheDocument();
  });

  it('offers an upload area when the grid has no images', () => {
    mockImages.mockReturnValue({ data: [] });

    renderTile();

    expect(screen.getByTestId('image-dropzone')).toBeInTheDocument();
  });

  it('shows the first thumb with a count and opens the Images tab', async () => {
    mockImages.mockReturnValue({ data: [testImage({ id: 'a' }), testImage({ id: 'b' }), testImage({ id: 'c' })] });
    const onUrlUpdate = renderTile();

    expect(screen.getByAltText('a.png')).toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
    expect(screen.queryByTestId('image-dropzone')).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Open 3 grid images'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(onUrlUpdate.mock.calls.at(-1)[0].queryString).toContain('gridTab=images');
  });
});
