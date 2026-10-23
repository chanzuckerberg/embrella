import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ImageAsset } from '@app/common/types/images';
import { ImageGallery } from './ImageGallery';
import { testImage } from './testImages';
import { PasteMode } from './usePasteImages';

// jsdom lacks the layout APIs these libraries measure with
jest.mock('embla-carousel-react', () => () => [jest.fn(), undefined]);
jest.mock('react-zoom-pan-pinch', () => ({
  TransformWrapper: ({ children }: { children: (controls: object) => React.ReactNode }) =>
    children({ zoomIn: jest.fn(), zoomOut: jest.fn(), resetTransform: jest.fn() }),
  TransformComponent: ({ children }: { children: React.ReactNode }) => children,
}));

function renderGallery(images: ImageAsset[]) {
  const props = {
    images,
    uploads: [],
    onFiles: jest.fn(),
    onRejected: jest.fn(),
    onDismissUpload: jest.fn(),
    onNotesChange: jest.fn().mockResolvedValue(undefined),
    onDelete: jest.fn().mockResolvedValue(undefined),
    paste: PasteMode.OFF,
  };
  const view = render(<ImageGallery {...props} />);
  return { ...view, props };
}

describe('ImageGallery', () => {
  it('shows only the uploader without images', () => {
    renderGallery([]);

    expect(screen.getByTestId('image-dropzone')).toBeInTheDocument();
    expect(screen.queryByLabelText('Notes')).not.toBeInTheDocument();
  });

  it('saves notes on blur when they changed', async () => {
    const image = testImage({ notes: 'thin ice' });
    const { props } = renderGallery([image]);
    const notes = screen.getByLabelText('Notes');

    await userEvent.click(notes);
    await userEvent.tab();
    expect(props.onNotesChange).not.toHaveBeenCalled();

    await userEvent.type(notes, ', B4 cracked');
    await userEvent.tab();
    expect(props.onNotesChange).toHaveBeenCalledWith(image, 'thin ice, B4 cracked');
  });

  it('flashes "Saved" after a save, then fades it out', async () => {
    renderGallery([testImage()]);

    await userEvent.type(screen.getByLabelText('Notes'), 'cracked');
    expect(screen.getByRole('status', { hidden: true })).not.toBeVisible();

    await userEvent.tab();
    await waitFor(() => expect(screen.getByRole('status')).toBeVisible());
    await waitFor(() => expect(screen.getByRole('status', { hidden: true })).not.toBeVisible(), { timeout: 3000 });
  });

  it('shows no "Saved" when saving fails', async () => {
    const { props } = renderGallery([testImage()]);
    props.onNotesChange.mockRejectedValue(new Error('offline'));

    await userEvent.type(screen.getByLabelText('Notes'), 'cracked');
    await userEvent.tab();

    await waitFor(() => expect(props.onNotesChange).toHaveBeenCalled());
    expect(screen.getByRole('status', { hidden: true })).not.toBeVisible();
  });

  it('deletes after confirmation', async () => {
    const image = testImage();
    const { props } = renderGallery([image]);

    await userEvent.click(screen.getByLabelText('Delete image'));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(props.onDelete).toHaveBeenCalledWith(image));
  });

  it('thumbs switch the shown image', async () => {
    renderGallery([testImage({ id: 'a' }), testImage({ id: 'b', notes: 'second' })]);

    await userEvent.click(screen.getByLabelText('Show b.png'));

    expect(screen.getByLabelText('Notes')).toHaveValue('second');
  });

  it('jumps to a newly uploaded image', () => {
    const first = testImage({ id: 'a' });
    const { props, rerender } = renderGallery([first]);

    rerender(<ImageGallery {...props} images={[first, testImage({ id: 'b', notes: 'new' })]} />);

    expect(screen.getByLabelText('Notes')).toHaveValue('new');
  });

  it('opens the fullscreen viewer and steps with arrow keys', async () => {
    renderGallery([testImage({ id: 'a' }), testImage({ id: 'b' })]);

    await userEvent.click(screen.getAllByAltText('a.png')[0]);
    const viewer = screen.getByRole('dialog', { name: /^a\.png/ });
    expect(within(viewer).getByText(/1 \/ 2/)).toBeInTheDocument();

    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('dialog', { name: /^b\.png/ })).toBeInTheDocument();
  });
});
