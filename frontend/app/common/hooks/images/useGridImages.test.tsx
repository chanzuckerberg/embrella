import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { uploadGridImage } from '@app/common/queries/imagesApi';
import { UploadStatus } from '@app/common/types/images';
import { pngFile, testImage } from '@app/common/components/images/testImages';
import { gridImagesKey, useGridImageUploads } from './useGridImages';

jest.mock('@app/common/queries/imagesApi', () => ({ uploadGridImage: jest.fn() }));

const mockUpload = uploadGridImage as jest.Mock;
const GRID_ID = 7;

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = jest.spyOn(client, 'invalidateQueries');
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const hook = renderHook(() => useGridImageUploads(GRID_ID), { wrapper });
  return { ...hook, invalidate };
}

// Lets a test settle each upload by hand
function deferredUploads() {
  const settlers: { resolve: () => void; reject: (error: Error) => void }[] = [];
  mockUpload.mockImplementation(
    () =>
      new Promise((resolve, reject) => {
        settlers.push({ resolve: () => resolve(testImage()), reject });
      })
  );
  return settlers;
}

afterEach(() => mockUpload.mockReset());

describe('useGridImageUploads', () => {
  it('uploads one file at a time and removes each on success', async () => {
    const settlers = deferredUploads();
    const { result, invalidate } = setup();

    act(() => result.current.add([pngFile('a.png'), pngFile('b.png')]));

    expect(mockUpload).toHaveBeenCalledTimes(1);
    expect(result.current.uploads.map((item) => item.status)).toEqual([UploadStatus.UPLOADING, UploadStatus.QUEUED]);

    await act(async () => settlers[0].resolve());
    await waitFor(() => expect(mockUpload).toHaveBeenCalledTimes(2));
    expect(result.current.uploads.map((item) => item.file.name)).toEqual(['b.png']);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: gridImagesKey(GRID_ID) });

    await act(async () => settlers[1].resolve());
    await waitFor(() => expect(result.current.uploads).toEqual([]));
  });

  it('keeps a failed upload with its message until dismissed, then continues', async () => {
    const settlers = deferredUploads();
    const { result } = setup();

    act(() => result.current.add([pngFile('bad.png'), pngFile('good.png')]));
    await act(async () => settlers[0].reject(new Error('Save a single page.')));

    await waitFor(() => expect(mockUpload).toHaveBeenCalledTimes(2));
    const [failed] = result.current.uploads;
    expect(failed).toMatchObject({ status: UploadStatus.FAILED, error: 'Save a single page.' });

    act(() => result.current.dismiss(failed.key));
    expect(result.current.uploads.map((item) => item.file.name)).toEqual(['good.png']);
  });

  it('shows client-side rejections without uploading', () => {
    const { result } = setup();

    act(() => result.current.reject(pngFile('huge.png'), 'File is larger than 100 MB.'));

    expect(mockUpload).not.toHaveBeenCalled();
    expect(result.current.uploads[0]).toMatchObject({
      status: UploadStatus.FAILED,
      error: 'File is larger than 100 MB.',
    });
  });
});
