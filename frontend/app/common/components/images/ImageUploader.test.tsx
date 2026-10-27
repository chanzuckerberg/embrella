import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UploadStatus } from '@app/common/types/images';
import { TOO_LARGE_MESSAGE, WRONG_TYPE_MESSAGE } from './constants';
import { ImageUploader, UploaderSize, clientRejection } from './ImageUploader';
import { pngFile } from './testImages';
import { PasteMode } from './usePasteImages';

function renderUploader(paste = PasteMode.DOCUMENT) {
  const props = {
    uploads: [],
    onFiles: jest.fn(),
    onRejected: jest.fn(),
    onDismiss: jest.fn(),
    size: UploaderSize.FULL,
    paste,
  };
  render(<ImageUploader {...props} />);
  return props;
}

function paste(target: Element, files: File[]) {
  const event = new Event('paste', { bubbles: true, cancelable: true });
  Object.defineProperty(event, 'clipboardData', { value: { files } });
  fireEvent(target, event);
}

describe('ImageUploader', () => {
  it('passes browsed images on', async () => {
    const props = renderUploader();
    const file = pngFile();

    await userEvent.upload(screen.getByLabelText('Upload images'), file);

    await waitFor(() => expect(props.onFiles).toHaveBeenCalledWith([file]));
  });

  it('rejects other file types with a message', async () => {
    const props = renderUploader();
    const pdf = new File(['%PDF'], 'notes.pdf', { type: 'application/pdf' });

    await userEvent.setup({ applyAccept: false }).upload(screen.getByLabelText('Upload images'), pdf);

    await waitFor(() => expect(props.onRejected).toHaveBeenCalledWith(pdf, WRONG_TYPE_MESSAGE));
    expect(props.onFiles).not.toHaveBeenCalled();
  });

  it('uploads pasted screenshots', () => {
    const props = renderUploader();
    const file = pngFile('image.png');

    paste(document.body, [file]);

    expect(props.onFiles).toHaveBeenCalledWith([file]);
  });

  it('uploads an image the clipboard holds twice only once', () => {
    const props = renderUploader();
    const [first, copy, other] = [pngFile('image.png', 10), pngFile('image.png', 10), pngFile('b.png', 20)];

    paste(document.body, [first, copy, other]);

    expect(props.onFiles).toHaveBeenCalledWith([first, other]);
  });

  it('leaves pastes into text fields alone', () => {
    const props = renderUploader();
    render(<textarea aria-label="Notes" />);

    paste(screen.getByLabelText('Notes'), [pngFile()]);

    expect(props.onFiles).not.toHaveBeenCalled();
  });

  it('ignores pastes when paste is off', () => {
    const props = renderUploader(PasteMode.OFF);

    paste(document.body, [pngFile()]);

    expect(props.onFiles).not.toHaveBeenCalled();
  });

  it('shows progress and failures', () => {
    render(
      <ImageUploader
        uploads={[
          { key: '1', file: pngFile('up.png'), status: UploadStatus.UPLOADING, progress: 0.5 },
          {
            key: '2',
            file: pngFile('bad.tif'),
            status: UploadStatus.FAILED,
            progress: 0,
            error: 'Save a single page.',
          },
        ]}
        onFiles={jest.fn()}
        onRejected={jest.fn()}
        onDismiss={jest.fn()}
        size={UploaderSize.COMPACT}
        paste={PasteMode.OFF}
      />
    );

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
    expect(screen.getByText('Save a single page.')).toBeInTheDocument();
    expect(screen.getByLabelText('Dismiss bad.tif')).toBeInTheDocument();
  });
});

describe('clientRejection', () => {
  it('accepts TIFF by extension when the browser reports no type', () => {
    expect(clientRejection(new File(['x'], 'atlas.TIF', { type: '' }))).toBeNull();
  });

  it('rejects oversized files', () => {
    const big = pngFile();
    Object.defineProperty(big, 'size', { value: 200 * 1024 * 1024 });

    expect(clientRejection(big)).toBe(TOO_LARGE_MESSAGE);
  });
});
