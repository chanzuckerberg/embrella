import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { SubmissionLogPanel } from './SubmissionLogPanel';

const originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
afterEach(() => {
  if (originalClipboard) Object.defineProperty(navigator, 'clipboard', originalClipboard);
  else Reflect.deleteProperty(navigator, 'clipboard');
});

it('announces successful log copying', async () => {
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<SubmissionLogPanel data={{ logs: 'saved output', source: 'stored' }} active={false} phase="prep" />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Log copied.');
  expect(writeText).toHaveBeenCalledWith('saved output');
});

it('offers a manual fallback when clipboard access fails', async () => {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: jest.fn().mockRejectedValue(new Error('denied')) },
  });
  render(<SubmissionLogPanel data={{ logs: 'saved output', source: 'stored' }} active={false} phase="push" />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Select the log text to copy it manually.');
});

it('hides AWS progress updates while retaining uploaded filenames and errors', async () => {
  const logs =
    '(calculating...)Completed 2.0 GiB/~4.0 GiB (31.0 MiB/s) with ~2 file(s) remaining\r' +
    'upload: tomo.mrc to s3://example/tomo.mrc\n' +
    'Completed 3.0 GiB/4.0 GiB (31.0 MiB/s) with 1 file(s) remaining\r' +
    'upload failed: other.mrc: AccessDenied';
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<SubmissionLogPanel data={{ logs, source: 'live' }} active phase="push" />);
  const output = screen.getByRole('region', { name: 'Upload log output' });
  expect(output).not.toHaveTextContent('Completed');
  expect(output).toHaveTextContent('upload: tomo.mrc');
  expect(output).toHaveTextContent('AccessDenied');
  fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Log copied.');
  expect(writeText).toHaveBeenCalledWith(logs);
});

it('preserves scroll position while reading, resets on phase changes, and follows the final output', () => {
  const view = render(<SubmissionLogPanel data={{ logs: 'sync', source: 'live' }} active phase="prep" />);
  const output = screen.getByRole('region', { name: 'Sync log output' });
  Object.defineProperties(output, {
    scrollHeight: { configurable: true, value: 1000 },
    clientHeight: { configurable: true, value: 200 },
  });
  output.scrollTop = 100;
  fireEvent.scroll(output);
  view.rerender(<SubmissionLogPanel data={{ logs: 'more sync', source: 'live' }} active phase="prep" />);
  expect(output.scrollTop).toBe(100);

  view.rerender(<SubmissionLogPanel data={{ logs: 'upload', source: 'live' }} active phase="push" />);
  expect(output.scrollTop).toBe(1000);

  Object.defineProperty(output, 'scrollHeight', { configurable: true, value: 1200 });
  view.rerender(
    <SubmissionLogPanel data={{ logs: 'upload complete', source: 'stored' }} active={false} phase="push" />
  );
  expect(output.scrollTop).toBe(1200);
});
